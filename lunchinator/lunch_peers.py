import os, codecs, socket
from copy import deepcopy
from time import time
from threading import Lock
from collections import deque
from lunchinator import get_settings, log_warning, log_exception, log_error, log_debug, log_info
from lunchinator.utilities import getTimeDifference

class LunchPeers(object):
    def __init__(self, controller):
        self._controller = controller
        
        self._memberIDs = set()  # of PeerIDs members: peers that sent their info, are active and belong to my group
        self._IP_seen = {}  # last seen timestamps by IP
        self._peer_info = {}  # information of every peer by IP
        self._idToIp = {}  # mapping from ID to a set of IPs
        
        self._groups = set()  # seen group names
        
        self.dontSendTo = set()  
        self._new_peerIPs = set()  # peers I have to ask for info 
        
        self._lock = Lock()
        
        self._initPeersFromFile()  
        
    def finish(self):
        self._writePeersToFile()
    
    ################ Group Operations #####################
    # no lock -> groups are not removed  
    def getGroups(self):  
        """Collection of all lunch groups"""
        return self._groups
    
    def addGroup(self, group_name):
        if group_name not in self._groups:
            self._groups.add(group_name)
            # TODO: what was the second parameter supposed to be?
            self._controller.groupAppended(group_name, self._groups)
            
    
    ################ IP Timestamp Operations #####################
    # no locks needed: timeouts are not removed
    def seenIP(self, ip):
        self._IP_seen[ip] = time() 
        
    def getIPLastSeen(self, ip):
        if ip in self._IP_seen:
            return self._IP_seen[ip]
        return None  
    
    # here we need a lock
    def getIDLastSeen(self, pID):
        with self._lock:
            if pID in self._idToIp:
                return max([self.getIPLastSeen(ip) for ip in self._idToIp[pID]])
            else:
                return -1
    
    ################ Member Operations #####################
    def addMemberByIP(self, ip):
        with self._lock:
            if ip in self._peer_info:
                self._addMember(self._peer_info[ip][u"ID"])
    
    def isMemberByIP(self, ip):
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u"ID"] in self._memberIDs
            else:
                return False
            
    def removeMembersByIP(self, toRemove=None):
        with self._lock:
            if toRemove == None:
                self._memberIDs.clear()
                return
                
            if type(toRemove) != set:
                toRemove = set(toRemove)
                
            for ip in toRemove:
                if ip in self._peer_info:
                    self._removeMember(self._peer_info[ip][u"ID"])
    
    def getMemberIPs(self):
        with self._lock:
            return [ self._idToIp[ID] for ID in self._memberIDs ]            
        
    def getMembers(self):
        """Members are peers, that send their INFO, are in my group, and were active recently"""
        return deepcopy(self._memberIDs)    
    
    def getReadyMembers(self):
        with self._lock:
            return set([x for x in self._memberIDs if self._checkInfoForReady(self._getPeerInfoByID(x)) ])
    
    def _addMember(self, pID):
        if pID not in self._memberIDs:
            log_debug("Peer %s is a member" % pID) 
            self._memberIDs.add(pID)           
            self._controller.memberAppended(pID, deepcopy(self._getPeerInfoByID(pID)))
        else: #something may have changed for the member data
            self._controller.memberUpdated(pID, deepcopy(self._getPeerInfoByID(pID)))
            
    def _removeMember(self, pID):
        if pID in self._memberIDs:
            self._memberIDs.remove(pID)
            self._controller.memberRemoved(pID)  
    
     
    
    
    ################ Peer Operations #####################            
    def removePeerIPs(self, toRemove):
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        with self._lock:
            for ip in toRemove:
                if ip in self._peer_info:
                    pID = self._peer_info.pop(ip)[u"ID"]
                    self._removePeerIPfromID(pID, ip)
                     
                        
    def getPeerInfoByIP(self, ip):
        """Returns the info dictionary for a peer or None if the ID is unknown"""
        with self._lock:
            if ip in self._peer_info:
                return deepcopy(self._peer_info[ip])
            
        return None
    
    def getPeerInfo(self, pID):
        """Returns the info dictionary for a peer or None if the ID is unknown"""
        with self._lock:
            return deepcopy(self._getPeerInfoByID(pID))
            
        return None
        
    def getPeerGroupByIP(self, ip):
        """Returns the name of the peer or None if not a peer"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u'group']
        return None    
    
    def getPeerName(self, pID):
        """Returns the name of the peer or None if not a peer"""
        with self._lock:
            i = self._getPeerInfoByID(pID)
            if i:
                return i[u'name']
        return None 
    
    def getPeerNameByIP(self, ip):
        """Returns the name of the peer or None if not a peer"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u'name']
        return None 
    
    def getPeerID(self, ip):
        """Returns the name of the peer or None if not a peer"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u'ID']
        return None 
    
    def getPeerIPs(self, pID=None):
        """Returns the name of the peer or None if not a peer"""
        if pID == None:
            return self._peer_info.keys()
        with self._lock:
            if pID in self._idToIp:
                return set(self._idToIp[pID])
        return [] 
    
    def isPeerReadyByIP(self, ip):
        with self._lock:
            if ip in self._peer_info:
                return self._checkInfoForReady(self._peer_info[ip])
        return False
    
    def createPeerByIP(self, ip, info={}):  
        with self._lock:      
            if ip not in self._peer_info:
                log_info("new peer: %s" % ip)
                # I add a new peer -> if I do not have an ID yet, the ID is the ip
                self._peer_info[ip] = dict({u"name":ip,
                                            u"group":u"",
                                            u"ID":ip}.items() + info.items())
                pID = self._peer_info[ip][u"ID"]
                self._addPeerIPtoID(pID, ip)
                    
                if not self._IP_seen.has_key(ip):
                    self._IP_seen[ip] = -1
                self._new_peerIPs.add(ip)
            
    def updatePeerInfoByIP(self, ip, newInfo):    
        with self._lock:    
            if ip in self._new_peerIPs:
                self._new_peerIPs.remove(ip)
            oldPID = self._peer_info[ip][u"ID"]
            self._peer_info[ip].update(newInfo)
            newPID = self._peer_info[ip][u"ID"]
            
            if newPID != oldPID:
                self._removePeerIPfromID(oldPID, ip)
                self._addPeerIPtoID(newPID, ip)
            else:
                # TODO(Hannes) this info is now the most recent for this ID
                self._controller.peerUpdated(newPID, deepcopy(self._peer_info[ip]))
                log_debug("%s has new info: %s; \n update was %s" % (ip, self._peer_info[ip], newInfo))
            
            own_group = get_settings().get_group()       
            
            if 0 == len(own_group) or self._peer_info[ip][u"group"] == own_group:
                self._addMember(newPID)
                self.addGroup(self._peer_info[ip][u"group"])
            else:
                self._removeMember(newPID)
                
    def removeInactive(self):
        """1. members that haven't been seen for <memberTimeout> seconds are removed, 
        2. peers that haven't been seen for <peerTimeout> seconds or have never been seen 
        are removed
        3. the new peers list is cleaned, you should try to call them before invoking this"""
        
        log_debug("Removing inactive members and peers")      
        try:            
            with self._lock:
                #copy before changing members-list, cannot change while iterating
                mIDs = deepcopy(self._memberIDs)
                for mID in mIDs:
                    for ip in self._idToIp[mID]:       
                        if time() - self._IP_seen[ip] > get_settings().get_member_timeout():
                            self._removeMember(mID)
                            break
             
                for ip in self._IP_seen:
                    if ip in self._peer_info and time() - self._IP_seen[ip] > get_settings().get_peer_timeout():
                        pID = self._peer_info[ip][u"ID"]
                        self._removePeerIPfromID(pID, ip)
                        del self._peer_info[ip]
                        
                self._new_peerIPs.clear()
        except:
            log_exception("Something went wrong while trying to clean up the list of peers and members")
    
    def getPeerInfoDict(self):
        """Returns all data stored in the peerInfo dict"""
        return deepcopy(self._peer_info)
            
    def getNewPeerIPs(self):
        return deepcopy(self._new_peerIPs)
    
    # unlocked private operation:        
    def _checkInfoForReady(self, p_info):        
        if p_info and p_info.has_key(u"next_lunch_begin") and p_info.has_key(u"next_lunch_end"):
            diff = getTimeDifference(p_info[u"next_lunch_begin"], p_info[u"next_lunch_end"])
            if diff == None:
                # illegal format, just assume ready
                return True
            return diff > 0
        return False
             
    def _removePeerIPfromID(self, pID, ip):   
        log_debug("Removing %s from ID: %s" % (ip, pID))
        self._idToIp[pID].remove(ip)
        
        if 0 == len(self._idToIp[pID]):
            # no IP associated with that ID -> remove peer
            self._removeMember(pID)
            self._idToIp.pop(pID)
            self._controller.peerRemoved(pID)  
     
    def _addPeerIPtoID(self, pID, ip):       
        if pID not in self._idToIp:
            self._idToIp[pID] = set()
            self._idToIp[pID].add(ip)   
            self._controller.peerAppended(pID, deepcopy(self._peer_info[ip]))
        else:
            self._idToIp[pID].add(ip)   
            
    def _getPeerInfoByID(self, pID):
        if pID not in self._idToIp:
            return None
        recentIP = list(self._idToIp[pID])[0]
        return self._peer_info[recentIP]     
    
    def _initPeersFromFile(self):
        p_file = get_settings().get_peers_file() if os.path.exists(get_settings().get_peers_file()) else get_settings().get_members_file()
        
        if os.path.exists(p_file):
            with codecs.open(p_file, 'r', 'utf-8') as f:    
                for line in f.readlines():
                    line = line.split()
                    hostn = line[0].strip()
                    peerId = unicode(hostn)
                    if len(line) > 1:
                        peerId = unicode(line[1].strip())
                        
                    if not hostn:
                        continue
                    try:
                        ip = unicode(socket.gethostbyname(hostn))
                        self.createPeerByIP(ip, {u"name":unicode(hostn), u"ID":peerId})
                    except socket.error, e:
                        log_warning("cannot find host specified in members_file by %s with name %s" % (p_file, hostn))
    
    def _writePeersToFile(self):
        try:
            if len(self._peer_info) > 1:
                with codecs.open(get_settings().get_peers_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    with self._lock:
                        for ip in self._peer_info.keys():
                            f.write(u"%s\t%s\n" % (ip, self._peer_info[ip][u"ID"]))
        except:
            log_exception("Could not write peers to %s" % (get_settings().get_peers_file()))    
        
    def __len__(self):
        return len(self._idToIp)    
        
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
    
    def __iter__(self):
        return self._idToIp.iterkeys().__iter__()
