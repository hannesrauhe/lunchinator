""" lunch_socket+exceptions, extendedMessages(Incoming/Outgoing)"""

import socket, errno, sys, math, hashlib
from lunchinator import convert_string, log_debug, log_error, log_warning

""" lunch_socket is the class to 
1. abstract sockets to support IPv6 and IPv4 sockets transparently (TODO)
2. provide extended messages (HELOX) to enable encrypted and signed messages 
as well as splitting of long messages"""
class lunch_socket(object):    
    def __init__(self):
        self.s = None
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        except:
            self.s = None
            raise
        
        self.port = 50000
        self.max_msg_length = 1024
    
    """ sends a message to an IP on the configured port, 
    
    @long If only message an IP are given and the message string is shorter than 
    the maximum length, it will be send as is.    
    If the message is longer or encryption/signatures are enabled, the message
    will be send as HELOX call.
    
    Split messages will be hashed and the hash becomes the messages identifier 
    for the receiver.
    If the message is split and signed, the signature will be used instead of the hash.
    
    @param msg messge as unicode object
    @param ip IP or hostname of receiver
    @param disable_split automatic message splitting can be disabled by setting to True 
    """        
    def send(self, msg, ip, disable_split=False):
        if not self.s:
            raise Exception("Cannot send. There is no open lunch socket")
        
        send_str = msg.encode('utf-8')
        if not disable_split and len(msg) > self.max_msg_length:
            xmsg = extMessageOutgoing(msg)
            send_str = xmsg.toString()        
        
        log_debug("Sending", msg, "to", ip.strip())
        try:
            self.s.sendto(send_str, (ip.strip(), self.port))
        except:
            # only warning message; happens sometimes if the host is not reachable
            log_warning("Message %s could not be delivered to %s: %s" % (msg, ip, str(sys.exc_info()[0])))
            raise

    """ receives a message from a socket and returns the received data and the sender's 
    address
    
    If the received message was split (HELOX) and is still incomplete
    the socket throws the split_call exception -> recv should be called again""" 
    def recv(self):
        if not self.s:
            raise Exception("Cannot recv. There is no open lunch socket")
        
        for attempts in range(0, 5):
            try:
                data, addr = self.s.recvfrom(self.max_msg_length)                
                ip = unicode(addr[0])
                
                log_debug(u"Incoming data from %s: %s" % (ip, convert_string(data))) 
                
                msg = u""
                if data.startswith("HELOX"):
                    xmsg = extMessageIncoming(data)
                    if not xmsg.isComplete():
                        raise split_call(xmsg.getSplitID())
                    msg = xmsg.getPlainMessage()
                else:                    
                    try:
                        msg = data.decode('utf-8')
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
        if not self.s:
            raise Exception("Cannot bind. There is no open lunch socket")
        
        self.s.bind(("", self.port)) 
        self.s.settimeout(5.0)
    
    """ closes the socket"""    
    def close(self):
        if self.s:
            self.s.close()
        self.s = None
    
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
        
    def hashPlainMessage(self):
        """returns a 4-character string
        TODO replace with real non-crypto hash function such as http://pypi.python.org/pypi/mmh3/2.0"""
        hashstr = hashlib.md5(self._plainMsg).digest()[:4]
        return hashstr
    
    def isSigned(self):
        return self._signed
    
    def isEncrypted(self):
        return self._encrypted
    
    def isCompressed(self):
        return self._compressedMsg != ""
    
    def isComplete(self):
        return len(self._fragments) and all(len(f) > 0 for f in self._fragments)
    
    def getPlainMessage(self):
        return self._plainMsg
    
    def getSplitID(self):
        return self._splitID
    
class extMessageIncoming(extMessage):        
    def addFragment(self, f):
        if self.isComplete():
            raise Exception("All fragments for this message were received already")
        
        expectedFragments = ord(f[7])
        if len(self._fragments)==0:
            '''first fragment that arrives: store ID and expected length'''
            self._fragments = expectedFragments * [""]
            self._splitID = f[8:12]
        else:   
            '''already have fragments: check ID and expected length''' 
            if len(self._fragments) != expectedFragments:
                raise Exception("Fragment does not belong to message: the number of expected fragments changed")
            if self.getSplitID() != f[8:12]:
                raise Exception("Fragment does not belong to message: the ID changed changed for one message")
        
        fragmentNum = ord(f[6])
        if fragmentNum >= expectedFragments:
            raise Exception("Malformed Message: The fragment's number is out of range")
        
        self._fragments[fragmentNum] = f
                
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
            
"""builds the extMessage from a plain message"""
class extMessageOutgoing(extMessage):
    
    """ @param outgoingMessage as unicode object """
    def __init__(self, outgoingMessage, fragment_size):
        super(extMessageOutgoing, self).__init__()
        self._plainMsg = outgoingMessage
        self._fragment_size = fragment_size - len("HELOX xx0000")
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
            raise Exception("Message to large to be send over lunch socket: %d byte"%msg_len)
        
        self._splitID = self.hashPlainMessage()
        
        self._fragments = ["HELOX " + chr(i/n) + chr(m) + self.getSplitID() + \
                           self._compressedMsg[i:i+n] for i in range(0, msg_len, n)]
        log_debug("Splitting %d Byte in %d segments of size %d"%(msg_len, m, n))
    
    def getFragments(self):
        return self._fragments
            
