from lunchinator import log_debug
import math, hashlib

""" Message classes """
    
class extMessage(object):
    """Extended Messages start with HELOX (will be ignored by older lunchinators), 
    are always compressed, and are split into fragments if necessary:
    Message looks like this:
    HELOX <V><a><b><hash><Compressed Message> where
    V - 1 byte specifying the protocol version
    a - 1 byte Number of the fragment
    b - 1 byte Number of expected fragments for this message
    hash - 4 byte hash to identify message
    
    <Compressed Message> starts with 1 stating compression used"""
    
    MAX_SUPPORTED_VERSION = 0
    
    BYTE_VERSION        = 6
    BYTE_FRAGNUM        = 7
    BYTE_EXPECTED_NUM   = 8
    BYTE_HASH_START     = 9
    BYTE_HASH_END       = 13 #exclusive
    BYTE_MSG_START      = 13
    
    def __init__(self):
        self._protocol_version = self.MAX_SUPPORTED_VERSION
        self._fragments = []
        self._plainMsg = u""
        self._encrypted = False
        self._compressedMsg = ""
        self._signed = False
        self._splitID = "0000"
    
    def isSigned(self):
        return self._signed
    
    def isEncrypted(self):
        return self._encrypted
    
    def isCompressed(self):
        return self._compressedMsg != ""
    
    def isComplete(self):
        return len(self._fragments) and all(len(f) > 0 for f in self._fragments)
    
    def getCompleteness(self):
        completeFragments = 0
        for f in self._fragments:
            if f:
                completeFragments += 1
        return float(completeFragments) / float(len(self._fragments))
    
    def getFragments(self):
        return self._fragments
    
    def getPlainMessage(self):
        return self._plainMsg
    
    def getSplitID(self):
        return self._splitID
    
    def getVersion(self):
        return self._protocol_version
        
    def hashPlainMessage(self):
        """returns a 4-character string
        TODO replace with real non-crypto hash function such as http://pypi.python.org/pypi/mmh3/2.0"""
        hashstr = hashlib.md5(self._plainMsg).digest()[:4]
        return hashstr
    
class extMessageIncoming(extMessage):       
    """ @param outgoingMessage as unicode object """
    def __init__(self, incomingMessage):
        super(extMessageIncoming, self).__init__()
        f = incomingMessage
        
        if not f.startswith("HELOX"):
            raise Exception("Malformed Message: Not an extended message fragment (no HELOX)")
        
        self._protocol_version = ord(f[self.BYTE_VERSION])
        
        if self._protocol_version > self.MAX_SUPPORTED_VERSION:
            raise Exception("Message sent by peer that uses a newer protocol version")
            #at this point we should send an extended message ourself to tell 
            #the other peer our version
        
        expectedFragments = ord(f[self.BYTE_EXPECTED_NUM])
        self._fragments = expectedFragments * [""]
        self._splitID = f[self.BYTE_HASH_START:self.BYTE_HASH_END]
        
        self._insertFragment(f)
        self._finalize()
        
    def addFragment(self, f):
        if self.isComplete():
            raise Exception("All fragments for this message were received already")
        if not f.startswith("HELOX"):
            raise Exception("Malformed Message: Not an extended message fragment (no HELOX)")
        
        expectedFragments = ord(f[self.BYTE_EXPECTED_NUM])
        '''already have fragments: check ID and expected length''' 
        if len(self._fragments) != expectedFragments:
            raise Exception("Fragment does not belong to message: the number of expected fragments changed")
        if self.getSplitID() != f[self.BYTE_HASH_START:self.BYTE_HASH_END]:
            raise Exception("Fragment does not belong to message: the ID changed changed for one message")
        
        self._insertFragment(f)
        self._finalize()
        
    def _insertFragment(self, f):        
        fragmentNum = ord(f[self.BYTE_FRAGNUM])
        if fragmentNum >= len(self._fragments):
            raise Exception("Malformed Message: The fragment's number is out of range")
        
        self._fragments[fragmentNum] = f
    
    def _finalize(self):            
        if self.isComplete():        
            for e in self._fragments:
                self._compressedMsg += e[self.BYTE_MSG_START:]
            self.decompress()
            if self.hashPlainMessage()!=self.getSplitID():
                raise Exception("Malformed Message: Checksum of message invalid")
    
    def decompress(self):
        if not self.isCompressed():
            return True
        
        if self._compressedMsg[0]=='z':
            import zlib
            self._plainMsg = zlib.decompress(self._compressedMsg[1:])
        else:
            raise Exception("Unknown Compression identified by '%s'"%self._compressedMsg[0])
        
    def merge(self, other):
        for f in other.getFragments():
            if len(f):
                self._insertFragment(f)
        self._finalize()
            
            
"""builds the extMessage from a plain message"""
class extMessageOutgoing(extMessage):
    HEADER_SIZE = len("HELOX vxx0000") # TODO why whitespace?
    
    """ @param outgoingMessage as unicode object """
    def __init__(self, outgoingMessage, fragment_size):
        super(extMessageOutgoing, self).__init__()
        self._plainMsg = outgoingMessage
        self._fragment_size = fragment_size - self.HEADER_SIZE
        if self._fragment_size < 1:
            raise Exception("Fragment size %d to small to hold header"%fragment_size)

        self.compress()
        
        self.split()
        
    def compress(self):
        import zlib
        if self.isCompressed():
            return True

        self._compressedMsg = "z"+zlib.compress(self._plainMsg)
        log_debug("Compression: %d -> %d"%(len(self._plainMsg), len(self._compressedMsg)))
        
    def split(self):
        msg_len = len(self._compressedMsg)
        n = self._fragment_size
        m = int(math.ceil(float(msg_len) / float(n)))
        if m > 128:
            raise Exception("Message too large to be sent over lunch socket: %d byte"%msg_len)
        
        self._splitID = self.hashPlainMessage()
        
        self._fragments = ["HELOX "+ chr(self._protocol_version) + chr(i/n) + chr(m) + self.getSplitID() + \
                           self._compressedMsg[i:i+n] for i in range(0, msg_len, n)]
        log_debug("Splitting %d Byte in %d segments of size %d"%(msg_len, m, n))
            
