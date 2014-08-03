""" lunch_socket+exceptions, extendedMessages(Incoming/Outgoing)"""

import socket, errno, math, hashlib
from lunchinator import get_settings, log_debug, log_error, log_warning, convert_string
import itertools, time

""" lunch_socket is the class to 
1. abstract sockets to support IPv6 and IPv4 sockets transparently (TODO)
2. provide extended messages (HELOX) to enable encrypted and signed messages 
as well as splitting of long messages"""
class lunch_socket(object):    
    LEGACY_MAX_LEN = 1024
    EXT_MSG_VERSION = 1526
    
    def __init__(self, peers):
        self._s = None
        try:
            self._s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        except:
            self._s = None
            raise
        
        self._peers = peers
        self._port = get_settings().get_udp_port()
        self._max_msg_length = get_settings().get_max_fragment_length()
        self._incomplete_messages = {}
    
    """ sends a message to an IP on the configured port, 
    
    @long If only message and IP are given and the message string is shorter than 
    the maximum length, it will be sent as is.    
    If the message is longer or encryption/signatures are enabled, the message
    will be send as HELOX call.
    
    Split messages will be hashed and the hash becomes the messages identifier 
    for the receiver.
    If the message is split and signed, the signature will be used instead of the hash.
    
    @param msg messge as unicode object
    @param ip IP or hostname of receiver
    @param disable_split automatic message splitting can be disabled by setting to True 
    """        
    def sendto(self, msg, ip, disable_extended=False):
        if not self._s:
            raise Exception("Cannot send. There is no open lunch socket")
        
        # TODO remove leading HELO_, never use HELOX for old-school messages (they won't become too long anyways)?
        
        if len(msg) > self._max_msg_length:                     
            if disable_extended:
                log_warning("Message to peer %s is too long and should be compressed/split,"%ip + \
                 "but extended message is disabled for this call")   
            else:
                peerversion = self._peers.getPeerCommitCount(pIP = ip)
                peerversion = peerversion if peerversion else 0
                if peerversion < self.EXT_MSG_VERSION:                
                    log_warning("Message to peer %s is too long and should be compressed/split,"%ip + \
                     "but peer has version %d and cannot receive extended messages"%peerversion) 
                    disable_extended = True
            
            if disable_extended:
                if len(msg) > self.LEGACY_MAX_LEN:
                    raise Exception("Message too large to be send over socket in one piece")
                else:
                    self._s.sendto(msg, (ip.strip(), self._port))
            else:
                log_debug("Sending as extended Message")
                xmsg = extMessageOutgoing(msg, self._max_msg_length)
                for f in xmsg.getFragments():
                    self._s.sendto(f, (ip.strip(), self._port))
        else:
            self._s.sendto(msg, (ip.strip(), self._port))
        
    

    """ receives a message from a socket and returns the received data and the sender's 
    address
    
    If the received message was split (HELOX) and is still incomplete
    the socket throws the split_call exception -> recv should be called again""" 
    def recv(self):
        if not self._s:
            raise Exception("Cannot recv. There is no open lunch socket")
        
        for _ in itertools.repeat(None, 5):
            try:
                data, addr = self._s.recvfrom(self._max_msg_length)                
                ip = unicode(addr[0])
                
                msg = u""
                if data.startswith("HELOX"):
                    xmsg = extMessageIncoming(data)
                    if not xmsg.isComplete():
                        s = xmsg.getSplitID()
                        if s in self._incomplete_messages:
                            incompMsg, _ = self._incomplete_messages[(ip,s)]
                            incompMsg.merge(xmsg)
                            xmsg = incompMsg
                            if xmsg.isComplete():
                                del self._incomplete_messages[(ip,s)]
                        else:
                            self._incomplete_messages[(ip,s)] = (xmsg, time.time())
                        
                        if not xmsg.isComplete():
                            raise split_call(xmsg.getSplitID())
                    msg = xmsg.getPlainMessage()
                else:
                    try:
                        msg = data
                    except:
                        log_error("Received illegal data from %s, maybe wrong encoding" % ip)
                        continue    
                    
                return msg, ip
            except socket.error as e:
                if e.errno != errno.EINTR:
                    raise
                
        raise Exception("While receiving: There were 5 EINTR errors in a row. " + \
                    "That seems wrong, please open an issue on http://github.com/hannesrauhe/lunchinator")
        
    """ binds the socket to every interface and the lunchinator port; sets a timeout"""    
    def bind(self):   
        if not self._s:
            raise Exception("Cannot bind. There is no open lunch socket")
        
        self._s.bind(("", self._port)) 
        self._s.settimeout(5.0)
    
    """ closes the socket"""    
    def close(self):
        if self._s:
            self.drop_incomplete_messages()
            self._s.close()
        self._s = None
        
    """ clean up the cache for incomplete messages """
    def drop_incomplete_messages(self):
        timeout = get_settings().get_peer_timeout()
        for msg, timestamp in self._incomplete_messages.itervalues():
            pass
        
    
class split_call(Exception):
    def __init__(self, splitID):
        self.value = "Message %s not complete yet"%splitID
        
    def __str__(self):
        return repr(self.value)
    
    def dummy(self):
        pass
    
""" Message classes """
    
class extMessage(object):
    """Extended Messages start with HELOX (will be ignored by older lunchinators), 
    are always compressed, and are split into fragments if necessary:
    Message looks like this:
    HELOX <a><b><hash><c><Compressed Message> where
    a - 1 byte Number of the fragment
    b - 1 byte Number of expected fragments for this message
    hash - 4 byte hash to identify message
    c - 1 byte stating compression used"""
    
    def __init__(self):
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
    
    def getFragments(self):
        return self._fragments
    
    def getPlainMessage(self):
        return self._plainMsg
    
    def getSplitID(self):
        return self._splitID
        
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
        
        expectedFragments = ord(f[7])
        self._fragments = expectedFragments * [""]
        self._splitID = f[8:12]
        
        self._insertFragment(f)
        self._finalize()
        
    def addFragment(self, f):
        if self.isComplete():
            raise Exception("All fragments for this message were received already")
        if not f.startswith("HELOX"):
            raise Exception("Malformed Message: Not an extended message fragment (no HELOX)")
        
        expectedFragments = ord(f[7])
#         if len(self._fragments)==0:
#             '''first fragment that arrives: store ID and expected length'''
#             self._fragments = expectedFragments * [""]
#             self._splitID = f[8:12]
#         else:   
        '''already have fragments: check ID and expected length''' 
        if len(self._fragments) != expectedFragments:
            raise Exception("Fragment does not belong to message: the number of expected fragments changed")
        if self.getSplitID() != f[8:12]:
            raise Exception("Fragment does not belong to message: the ID changed changed for one message")
        
        self._insertFragment(f)
        self._finalize()
        
    def _insertFragment(self, f):        
        fragmentNum = ord(f[6])
        if fragmentNum >= len(self._fragments):
            raise Exception("Malformed Message: The fragment's number is out of range")
        
        self._fragments[fragmentNum] = f
    
    def _finalize(self):            
        if self.isComplete():        
            for e in self._fragments:
                self._compressedMsg += e[12:]
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
    HEADER_SIZE = len("HELOX xx0000") # TODO why whitespace?
    
    """ @param outgoingMessage as unicode object """
    def __init__(self, outgoingMessage, fragment_size):
        super(extMessageOutgoing, self).__init__()
        self._plainMsg = outgoingMessage
        self._fragment_size = fragment_size - self.HEADER_SIZE
        if self._fragment_size < 1:
            raise Exception("Fragment size %d to small to hold header"%fragment_size)

        self.compress()
        
#         if len(self._compressedMsg) > self._fragment_size:
        self.split()
#         else:
#             self._fragments.append("HELOX "+ chr(0) + chr(1) + self.getSplitID() + self._compressedMsg)
        
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
        
        self._fragments = ["HELOX " + chr(i/n) + chr(m) + self.getSplitID() + \
                           self._compressedMsg[i:i+n] for i in range(0, msg_len, n)]
        log_debug("Splitting %d Byte in %d segments of size %d"%(msg_len, m, n))
            
