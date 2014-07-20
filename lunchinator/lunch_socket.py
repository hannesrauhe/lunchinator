""" lunch_socket+exceptions, extendedMessages(Incoming/Outgoing)"""

import socket, errno, sys
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
    def __init(self):
        self._extMsgStr = u""
        self._plainMsg = u""
        self._encrypted = False
        self._compressed = False
        self._complete = False
        self._signed = False
        self._splitID = ""
        
    def isSigned(self):
        return self._signed
    
    def isEncrypted(self):
        return self._encrypted
    
    def isCompressed(self):
        return self._compressed
    
    def isComplete(self):
        return self._complete
    
    def toString(self):
        return self._extMsgStr.encode('utf-8')
    
    def toUnicode(self):
        return self._extMsgStr
    
    def getPlainMessage(self):
        return self._plainMsg
    
    def getSplitID(self):
        return self._splitID
    
class extMessageIncoming(extMessage):
    def __init__(self, incomingString):
        super(extMessageIncoming, self).__init__()
        self._extMsgStr = convert_string(incomingString)
        
"""builds the extMessage from a plain message"""
class extMessageOutgoing(extMessage):
    
    """ @param outgoingMessage as unicode object """
    def __init__(self, outgoingMessage):
        super(extMessageOutgoing, self).__init__()
        self._plainMsg = outgoingMessage
