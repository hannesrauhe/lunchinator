from time import time
from threading import Lock
from lunchinator import get_settings

class LunchPeers(object):
    def __init__(self, controller):
        self._activePeerIDs = set()  # contains IDs of active peers
        self._IDToIP = {}  # mapping from IDs to peer IDs
        self._IPToID = {}  # mapping from peer IDs to IPs
        self._peer_timeout = {}  # last seen timestamps
        self._peer_info = {}
        self._groups = set()
        self._lock = Lock()
        self._controller = controller
        self.dontSendTo = set()
        
        # TODO implement really unique IDs (peerID changes)
    
    def getActivePeers(self):
        """Collection of all peers, including peers from different groups"""
        return self._activePeerIDs
    
    def getGroups(self):  
        """Collection of all lunch groups"""
        return self._groups
    
    def isMemberInMyGroup(self, peerID):
        return self.getPeerInfo(peerID) != None and \
            u"group" in self.getPeerInfo(peerID) and\
            self.getPeerInfo(peerID)["group"] == get_settings().get_group()
    
    def getGroupPeers(self):
        """Collection of active peers in my own group"""
        return [ip for ip in self.getActivePeers() if self.isMemberInMyGroup(ip)]
    
    def getSendTargets(self):
        """Collection of the peers you should send messages to"""
        # TODO maintain dontSendTo
        return set(self.getGroupPeers()) - self.dontSendTo
    
    def getIPOfPeer(self, peerID):
        """Returns the latest active IP for the given peer"""
        if peerID in self._IDToIP:
            return self._IDToIP[peerID][-1]
        return None
    
    def getPeerID(self, ip):
        """Returns the peer ID for a given IP"""
        if ip in self._IPToID:
            return self._IPToID[ip]
        return None
    
    def getPeerInfo(self, peerID):
        """Returns the info dictionary for a peer or None if the ID is unknown"""
        if peerID in self._peer_info:
            return self._peer_info[peerID]
        return None
    
    def _addPeer(self, peerID, name, inform=True, overwriteName=True):
        # insert name into info dict
        infoDict = {}
        if peerID in self._peer_info:
            infoDict = self._peer_info[peerID]
        if overwriteName or u'name' not in infoDict:
            infoDict[u'name'] = name

        didAppend = False
        didUpdate = False
        with self._lock:
            self._peer_info[peerID] = infoDict
            if not peerID in self._activePeerIDs:
                self._activePeerIDs.add(peerID)
                if inform:
                    didAppend = True
            elif inform:
                didUpdate = True
                
        if didAppend:
            self._memberAppended(peerID)
        if didUpdate:
            self._memberUpdated(peerID)
    
    def _addPeerIP(self, peerID, ip):
        """Add an IP you don't know yet (or that is inactive)"""
        self._IPToID[ip] = peerID
        
        if peerID in self._IDToIP:
            ips = self._IDToIP[peerID]
            newPeer = False
        else:
            ips = []
            newPeer = True
        ips.append(ip)
        
        self._IDToIP[peerID] = ips
        if newPeer:
            self._addPeer(ip, ip, overwriteName=False)
    
    def _addPeerID(self, peerID, ip):
        """Adds a peerID you don't know yet. The IP might be known already."""
        if ip in self._IPToID:
            # we just received the peer ID for an IP
            oldPeerID = self._IPToID[ip]
            self._remove_member(oldPeerID)
            
            if oldPeerID in self._peer_info:
                # store info dictionary for new peer ID
                with self._lock:
                    self._peer_info[peerID] = self._peer_info[oldPeerID]
                    del self._peer_info[oldPeerID]
            
        # in any case, add the new peer.
        self._addPeerIP(peerID, ip)
    
    def _memberAppended(self, peerID):
        self._controller.memberAppended(peerID, self._peer_info[peerID])
    
    def _memberUpdated(self, peerID):
        self._controller.memberUpdated(peerID, self._peer_info[peerID])
    
    def _memberRemoved(self, peerID):
        self._controller.memberRemoved(peerID)
    
    def _remove_member(self, peerID):
        didRemove = False
        with self._lock: 
            if peerID in self._activePeerIDs:
                self._activePeerIDs.remove(peerID)
                # remove ID / IP mapping
                for ip in self._IDToIP[peerID]:
                    del self._IPToID[ip]
                del self._IDToIP[peerID]
                
                didRemove = True
            
        if didRemove:
            self._memberRemoved(peerID)
    
    def removeMembers(self, toRemove):
        if type(toRemove) != set:
            toRemove = set(toRemove)

        for peerID in toRemove:
            self._remove_member(peerID)        
    
    def knowsIP(self, ip):
        return ip in self._IPToID
    
    def knowsID(self, peerID):
        return peerID in self._IDToIP
    
    def seenPeer(self, ip):
        if not ip.startswith("127."):
            if not self.knowsIP(ip):
                self._addPeerIP(ip, ip)
            
            peerID = self.getPeerID(ip)
            
            # move last seen IP to back of list
            idx = self._IDToIP[peerID].index(ip)
            if idx != len(self._IDToIP[peerID]) - 1:
                # swap to last position
                self._IDToIP[peerID][-1], self._IDToIP[peerID][idx] = self._IDToIP[peerID][idx], self._IDToIP[peerID][-1] 
            self._peer_timeout[peerID] = time()
            
    def memberLeft(self, ip):
        peerID = self.getPeerID(ip)
        self._remove_member(peerID)
    
    def peerNameReceived(self, peerID, ip, name, inform=True):
        if peerID and not self.knowsID(peerID):
            self._addPeerID(peerID, ip)
            
        if not self.knowsIP(ip):
            self._addPeerIP(peerID if peerID else ip, ip)
        self._addPeer(peerID if peerID else self.getPeerID(ip), name, inform=inform)

    def updatePeerInfo(self, ip, newInfo):
        oldPeerID = self.getPeerID(ip)
        # TODO if there is a new peer ID, update!
            
        peer_group = newInfo[u"group"] if u"group" in newInfo else ""     
        peer_name = newInfo[u"name"] if u"name" in newInfo else oldPeerID
        own_group = get_settings().get_group()       
        
        group_unchanged = self.getPeerInfo(oldPeerID) != None and \
                          u"group" in self.getPeerInfo(oldPeerID) and \
                          self.getPeerInfo(oldPeerID)[u"group"] == peer_group
        with self._lock:
            self._peer_info[oldPeerID] = newInfo
        
        if group_unchanged:
            if peer_group == own_group:
                self._memberUpdated(oldPeerID)
        else:
            if peer_group not in self._groups:
                self._groups.add(peer_group)
                self._controller.groupAppended(peer_group, self._groups)
            if peer_group == own_group:
                self._addPeer(oldPeerID, peer_name)
                # TODO is this necessary?
                #self._memberUpdated(oldPeerID)
            else:
                self._remove_member(oldPeerID)
        
        # TODO the new one!
        return oldPeerID
    
    def getTimedOutMembers(self, timeout):
        result = set()
        for peerID in self.getActivePeers():
            if peerID in self._peer_timeout:
                if time() - self._peer_timeout[peerID] > timeout:
                    result.add(peerID)
            else:
                result.add(peerID)

        return result
                
    def getTimeout(self, peerID):
        if peerID in self._peer_timeout:
            return self._peer_timeout[peerID]
        return None
                
    def ipForMemberName(self, name):
        for peerID, infoDict in self._peer_info.iteritems():
            if u'name' in infoDict and infoDict[u'name'] == name:
                if peerID in self._IDToIP:
                    return self.getIPOfPeer(peerID)
        return None
    
    def getPeerInfoDict(self):
        return self._peer_info
    
    def lockMembers(self):
        self._lock.acquire()
        
    def releaseMembers(self):
        self._lock.release()
        
    def __len__(self):
        return len(self.getActivePeers())
    
    def __iter__(self):
        return self.getActivePeers().__iter__()