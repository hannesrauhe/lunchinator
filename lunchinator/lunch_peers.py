import os, codecs, socket
from time import time
from threading import Lock
from lunchinator import get_settings, log_warning, log_exception, log_error, log_debug, log_info
from lunchinator.utilities import getTimeDifference

class LunchPeers(object):
    def __init__(self, controller):
        self._controller = controller
        
        self._members = set()  # members: peers that sent their info, are active and belong to my group
        self._peer_timeout = {}  # last seen timestamps
        self._peer_info = {}
        self._groups = set()
        
        self.dontSendTo = set()  
        self._new_peers = set()  # peers I have to ask for info 
        
        # todo: it's a mess, what looks do i need?
        self._peerLock = Lock()
        self._memberLock = Lock()
        
        self._initPeersFromFile()  
        
    # todo think about how to update group set (when to remove a group)    
    def getGroups(self):  
        """Collection of all lunch groups"""
        return self._groups
    
    def addGroup(self, group_name):
        if group_name not in self._groups:
            self._groups.add(group_name)
            # TODO: what was the second parameter supposed to be?
            self._controller.groupAppended(group_name, self._groups)
    
    def isMember(self, ip):
        return ip in self._members
        
    def getMembers(self):
        """Members are peers, that send their INFO, are in my group, and were active """
        return self._members    
    
    def addMember(self, ip):
        if ip in self._peer_info:
            log_debug("Peer %s is a member" % ip)
            with self._memberLock:
                self._members.add(ip)            
            self._controller.memberAppended(ip, self.getPeerInfo(ip))
        
    def removeMembers(self, toRemove=None):
        if toRemove == None:
            self._members.clear()
            return
            
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        with self._memberLock:
            for ip in toRemove:
                if ip in self._members:
                    self._members.remove(ip)
                    self._controller.memberRemoved(ip)
    
    def seenPeer(self, ip):
        self._peer_timeout[ip] = time()        
    
    def removePeers(self, toRemove):
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        with self._peerLock:
            for ip in toRemove:
                if ip in self._peer_info:
                    self._peer_info.pop()
                    self._controller.peerRemoved(ip)
    
    def getPeerInfo(self, ip):
        """Returns the info dictionary for a peer or None if the ID is unknown"""
        if ip in self._peer_info:
            return self._peer_info[ip]
        return None
    
    def getPeerInfoDict(self):
        """Returns all data stored in one dict"""
        return self._peer_info
    
    def getPeerName(self, ip):
        """Returns the name of the peer or None if not a peer"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'name']
        return None 
    
    def getPeerID(self, ip):
        """Returns the name of the peer or None if not a peer"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'ID']
        return None 
     
    def getPeerGroup(self, ip):
        """Returns the name of the peer or None if not a peer"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'group']
        return None    

    def getPeers(self):
        return self._peer_info.keys()
    
    def isPeerReady(self, ip):
        p = self.getPeerInfo(ip)
        if p and p.has_key(u"next_lunch_begin") and p.has_key(u"next_lunch_end"):
            diff = getTimeDifference(p[u"next_lunch_begin"], p[u"next_lunch_end"])
            if diff == None:
                # illegal format, just assume ready
                return True
            return diff > 0
        return False
    
    def createPeer(self, ip, info={}):        
        if ip not in self._peer_info:
            log_info("new peer: %s" % ip)
            with self._peerLock:
                self._peer_info[ip] = dict({u"name":ip, 
                                            u"group":u"", 
                                            u"ID":unicode(len(self._peer_info))}.items() + info.items())
            self._new_peers.add(ip)     
            self._controller.peerAppended(ip, self._peer_info[ip])
            
    def updatePeerInfo(self, ip, newInfo):        
        if ip in self._new_peers:
            self._new_peers.remove(ip)
            
        with self._peerLock:
            self._peer_info[ip].update(newInfo)
            self._controller.peerUpdated(ip, self._peer_info[ip])
        
        log_debug("%s has new info: %s; \n update was %s" % (ip, self._peer_info[ip], newInfo))
            
        own_group = get_settings().get_group()       
        
        if ip not in self._members and 0 == len(own_group):
            self.addMember(ip)
            self.addGroup(self._peer_info[ip][u"group"])
        elif ip not in self._members and self._peer_info[ip][u"group"] == own_group:
            self.addMember(ip)
            self.addGroup(self._peer_info[ip][u"group"])
        elif ip in self._members and self._peer_info[ip][u"group"] != own_group:
            self.removeMembers(ip)
                    
    def getTimeout(self, ip):
        if ip in self._peer_timeout:
            return self._peer_timeout[ip]
        return None
    
    def lockPeers(self):
        self._peerLock.acquire()
        
    def releasePeers(self):
        self._peerLock.release()
            
    def removeInactive(self):
        """1. members that haven't been seen for <memberTimeout> seconds are removed, 
        2. peers that haven't been seen for <peerTimeout> seconds or have never been seen 
        are removed"""        
        try:            
            m2remove = []
            for ip in self._members:
                # todo: get_settings().get_member_timeout():
                if time() - self._peer_timeout[ip] > 300:
                    m2remove.append(ip)
            
            if len(m2remove):
                log_debug("Removing inactive members:", m2remove)
                self.removeMembers(m2remove)    
                
            p2remove = []                       
            for ip in self._peer_timeout:
                # todo: get_settings().get_peer_timeout():
                if time() - self._peer_timeout[ip] > 10000:
                    p2remove.append(ip)
                
            if len(p2remove):
                log_debug("Removing inactive peers:", p2remove)
                self.removePeers(p2remove)
        except:
            log_exception("Something went wrong while trying to clean up the list of active members")
            
        # todo: remove empty Groups?
    
    def finish(self):
        self._writePeersToFile()
    
    def _initPeersFromFile(self):
        p_file = get_settings().get_peers_file() if os.path.exists(get_settings().get_peers_file()) else get_settings().get_members_file()
        
        if os.path.exists(p_file):
            with codecs.open(p_file, 'r', 'utf-8') as f:    
                for line in f.readlines():
                    line = line.split()
                    hostn = line[0].strip()
                    peerId = unicode(hostn)
                    if len(line)>1:
                        peerId = unicode(line[1].strip())
                        
                    if not hostn:
                        continue
                    try:
                        ip = unicode(socket.gethostbyname(hostn))
                        self.createPeer(ip, {u"name":unicode(hostn), u"ID":peerId})
                    except:
                        log_warning("cannot find host specified in members_file by %s with name %s" % (p_file, hostn))
    
    def _writePeersToFile(self):
        try:
            if len(self._peer_info) > 1:
                with codecs.open(get_settings().get_peers_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    for ip in self._peer_info.keys():
                        f.write(u"%s\t%s\n" % (ip, self.getPeerID(ip)))
        except:
            log_exception("Could not write all members to %s" % (get_settings().get_peers_file()))    
        
    def __len__(self):
        return len(self._peer_info)    
        
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
    
    def __iter__(self):
        return self._peer_info.iterkeys().__iter__()
