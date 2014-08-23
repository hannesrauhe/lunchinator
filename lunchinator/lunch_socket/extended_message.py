from lunchinator import log_debug
import math, hashlib

""" Message classes """
    
class extMessage(object):
    """Extended Messages start with HELOX (will be ignored by older lunchinators), 
    are always compressed, and are split into fragments if necessary:
    Message looks like this:
    HELOX <V><a><b><hash><Message> where
    V - 1 byte specifying the protocol version
    a - 1 byte Number of the fragment
    b - 1 byte Number of expected fragments for this message
    hash - 4 byte hash to identify message
    
    <Message> starts with 1 Byte stating compression,signature,encryption and hash used,
    2 bit each for first protocol version
    hash:        00 - MD5[0:4]
    compression: 00 - None,     01 - zlib
    encryption:  00 - None,     01 - GPG
    signature:   00 - None,     01 - GPG"""
    
    MAX_SUPPORTED_VERSION = 0
    HEADER_SIZE         = len("HELOX vxx0000")    
    BYTE_VERSION        = 6
    BYTE_FRAGNUM        = 7
    BYTE_EXPECTED_NUM   = 8
    BYTE_HASH_START     = 9
    BYTE_HASH_END       = 13 #exclusive (used for slice notation)
    BYTE_MSG_START      = 13
    
    def __init__(self):
        self._protocol_version = self.MAX_SUPPORTED_VERSION
        self._fragments = []
        self._plainMsg = u""
        self._splitID = "0000"
        self._statusByte = 0b00000000 
    
    def isSigned(self):
        return bool(self._statusByte & 0b00000011)
    
    def isEncrypted(self):
        return bool(self._statusByte & 0b00001100)
    
    def isCompressed(self):
        return bool(self._statusByte & 0b00110000)
    
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
        
    """ @brief returns a 4-character string used as message ID,
    uses the hash function according to the status byte"""
    def hashPlainMessage(self):
        """TODO replace with real non-crypto hash function 
        such as http://pypi.python.org/pypi/mmh3/2.0"""
        
        if 0b00000000 == (self._statusByte & 0b11000000):
            hashstr = hashlib.md5(self._plainMsg).digest()[:4]
        else:
            raise Exception("Hash function used for Split ID unknown")
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
            pipe_value = ""        
            for e in self._fragments:
                pipe_value += e[self.BYTE_MSG_START:]
            
            self._statusByte = ord(pipe_value[0])
            pipe_value = pipe_value[1:]
            pipe_value = self._decompress(pipe_value)
            pipe_value = self._decrypt_and_verify(pipe_value)
            
            self._plainMsg = pipe_value
            if self.isSigned():
                if self.hashPlainMessage()!=self.getSplitID():
                    raise Exception("Malformed Message: Checksum of message invalid")
    
    def _decompress(self, value):
        if not self.isCompressed():
            return value
        if 0b010000 == (self._statusByte & 0b00110000):
            import zlib
            return zlib.decompress(value)
        else:
            raise Exception("Unknown Compression identified by '%s'"%self._compressedMsg[0])
        
    def _decrypt_and_verify(self, value):
        if not self.isEncrypted():
            res = value
            
        if self.isSigned():
            pass
        
        return res
        
    def merge(self, other):
        for f in other.getFragments():
            if len(f):
                self._insertFragment(f)
        self._finalize()
            
            
"""builds the extMessage from a plain message"""
class extMessageOutgoing(extMessage):    
    """ @param outgoingMessage as unicode object """
    def __init__(self, outgoingMessage, fragment_size, sign_key=None, encrypt_key=None, compress="zlib"):
        super(extMessageOutgoing, self).__init__()
        self._plainMsg = outgoingMessage
        self._fragment_size = fragment_size - self.HEADER_SIZE
        if self._fragment_size < 1:
            raise Exception("Fragment size %d to small to hold header"%fragment_size)
        
        pipe_value = outgoingMessage
        if encrypt_key:
            pipe_value = self._encrypt_sign(pipe_value, encrypt_key, sign_key)
        elif sign_key:
            pipe_value = self._sign(pipe_value, sign_key)
            
        if compress=="zlib":
            pipe_value = self._compress(pipe_value)        
        
        self._split(pipe_value)
        
    ''' @brief value will be encrypted and optionally signed and returned'''
    def _encrypt_sign(self, value, encrypt_key, sign_key=None):
        #import gpg
        
        self._statusByte = 0b00000100 | self._statusByte
        if sign_key:
            self._statusByte = 0b00000001 | self._statusByte
#         c = gpg.encrypt(value, encrypt_key, sign=sign_key, always_trust=True)
#         return str(c)
        return value
    
    ''' @brief value will be signed and not encrypted'''
    def _sign(self, value, sign_key=None):
        #import gpg
        
        self._statusByte = 0b00000001 | self._statusByte
#         c = gpg.sign(value, keyid=sign_key, always_trust=True)
#         return str(c)
        return value
    
    ''' @brief value will be compressed and returned'''
    def _compress(self, value):
        import zlib

        compressedMsg = zlib.compress(value)
        self._statusByte = 0b00010000 | self._statusByte
        log_debug("Compression: %d -> %d"%(len(value), len(compressedMsg)))
        return compressedMsg
    
    ''' @brief value will be split into fragments and an ID will be assigned and stored in instance variables''' 
    def _split(self, value):
        msg_len = len(value)
        n = self._fragment_size
        m = int(math.ceil(float(msg_len) / float(n)))
        if m > 128:
            raise Exception("Message too large to be sent over lunch socket: %d byte"%msg_len)
        
        #set statusByte to chose hash function
        self._splitID = self.hashPlainMessage()
        
        value = chr(self._statusByte) + value
        
        self._fragments = ["HELOX "+ chr(self._protocol_version) + chr(i/n) + chr(m) + self.getSplitID() + \
                           value[i:i+n] for i in range(0, msg_len, n)]
        log_debug("Splitting %d Byte in %d segments of size %d"%(msg_len, m, n))
        
            
