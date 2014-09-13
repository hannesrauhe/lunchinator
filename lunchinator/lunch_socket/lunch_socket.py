""" lunch_socket+exceptions, extendedMessages(Incoming/Outgoing)"""

import socket, errno
from lunchinator import get_settings
from lunchinator.log import getCoreLogger
from lunchinator.logging_mutex import loggingMutex
from lunchinator.lunch_socket.extended_message import extMessageOutgoing,\
    extMessageIncoming
import itertools, time

class lunchSocket(object):    
    """ lunch_socket is the class to 
    1. abstract sockets to support IPv6 and IPv4 sockets transparently (TODO)
    2. provide extended messages (HELOX) to enable encrypted and signed messages 
    as well as splitting of long messages"""
    
    LEGACY_MAX_LEN = 1024
    EXT_MSG_VERSION = 1660
    
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
        
        self._incMsgLock = loggingMutex("dropIncompleteMsg", logging=get_settings().get_verbose())
    
          
    def sendto(self, msg, ip, disable_extended=False):
        """ sends a message to an IP on the configured port, 
    
        @long If only message and IP are given and the message string is shorter than 
        the maximum length, it will be sent as is.    
        If the message is longer or encryption/signatures are enabled, the message
        will be send as HELOX call.
        
        Split messages will be hashed and the hash becomes the messages identifier 
        for the receiver.
        If the message is split and signed, the signature will be used instead of the hash.
        
        @param msg messge as unicode object
        @type msg: unicode
        @param ip IP or hostname of receiver
        @param disable_split automatic message splitting can be disabled by setting to True 
        """  
        
        if not self._s:
            raise Exception("Cannot send. There is no open lunch socket")
        
        ip = ip.strip()
        
        if len(msg) > self._max_msg_length:                     
            if disable_extended:
                getCoreLogger().warning("Message to peer %s is too long and should be compressed/split, " + \
                 "but extended message is disabled for this call", ip)   
            else:
                peerversion = self._peers.getPeerCommitCount(pIP = ip)
                peerversion = peerversion if peerversion else 0
                if peerversion < self.EXT_MSG_VERSION:                
                    getCoreLogger().warning("Message to peer %s is too long and should be compressed/split, " + \
                     "but peer has version %d and cannot receive extended messages", ip, peerversion) 
                    disable_extended = True
        else:
            disable_extended = True
                    
        if disable_extended:
            if len(msg) > self.LEGACY_MAX_LEN:
                raise Exception("Message too large to be send over socket in one piece")
            else:
                self._s.sendto(msg.encode('utf-8'), (ip, self._port))
        else:
            getCoreLogger().debug("Sending as extended Message")
            xmsg = extMessageOutgoing(msg, self._max_msg_length)
            for f in xmsg.getFragments():
                self._s.sendto(f, (ip, self._port))
        
    def broadcast(self, msg):
        """
        @type msg: unicode
        """
         
        try:
            self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            if len(msg) > self.LEGACY_MAX_LEN:
                getCoreLogger().debug("Broadcasting as extended Message")
                xmsg = extMessageOutgoing(msg, self._max_msg_length)
                for f in xmsg.getFragments():
                    self._s.sendto(f, ('255.255.255.255', self._port))
            else:
                getCoreLogger().debug("Broadcasting")
                self._s.sendto(msg.encode('utf-8'), ('255.255.255.255', self._port))
        except:
            getCoreLogger().warning("Problem while broadcasting", exc_info=1)
    

    def recv(self):
        """ receives a message from a socket and returns the received data and the sender's 
        address
        
        If the received message was split (HELOX) and is still incomplete
        the socket throws the split_call exception -> recv should be called again
        
        @rtype: (extMessageIncoming, unicode)
        """
        
        if not self._s:
            raise Exception("Cannot recv. There is no open lunch socket")
        
        for _ in itertools.repeat(None, 5):
            try:
                rawdata, addr = self._s.recvfrom(self.LEGACY_MAX_LEN) 
                ip = unicode(addr[0])
                
                xmsg = extMessageIncoming(rawdata)
                if not xmsg.isComplete():
                    #it's a split message
                    s = xmsg.getSplitID()
                    with self._incMsgLock:
                        if (ip,s) in self._incomplete_messages:
                            incompMsg, _ = self._incomplete_messages[(ip,s)]
                            xmsg.merge(incompMsg)                       
                    
                        if not xmsg.isComplete():
                            self._incomplete_messages[(ip,s)] = (xmsg, time.time())
                            raise splitCall(ip, xmsg)
                        else:
                            del self._incomplete_messages[(ip,s)]
                
                return xmsg, ip
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
            self._s.close()
        self._s = None
        
    """ clean up the cache for incomplete messages """
    def drop_incomplete_messages(self):
        timeout = get_settings().get_peer_timeout()
        drop_ids = []
        
        with self._incMsgLock:
            for ID, (msg, timestamp) in self._incomplete_messages.iteritems():
                if timestamp + timeout < time.time() :
                    drop_ids.append(ID)
                    
            for ID in drop_ids:
                del self._incomplete_messages[ID]
        
    
class splitCall(Exception):
    def __init__(self, ip, xmsg):
        self.value = "Message from %s not complete (%.2f%%) yet"%(ip, xmsg.getCompleteness()*100)
        
    def __str__(self):
        return repr(self.value)
    
