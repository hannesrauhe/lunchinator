import os, codecs, socket, json
from copy import deepcopy
from time import time
from lunchinator import get_settings, log_warning, log_exception, log_debug, log_info, get_notification_center
from lunchinator.utilities import getTimeDifference
from lunchinator.logging_mutex import loggingMutex
import logging

        
class LunchPeers(object):    
    """This class holds information about all peers known to the lunchinator,
    Terminology:
    * a peer is anyone who sent a UDP packet to the lunchinator port
    a peer can either be identified by its IP and additionally by any ID it told us
    (usually an UUID). This way a peer that changed its IP (e.g. because of switching 
    between LAN and WLAN, or because of DHCP) can be recognised later. If no ID was 
    sent, the ID is the IP. Peers are removed after a defined timeout (default: 10000 sec 
    after the last contact or within approx. a minute if they are not reacting to our 
    requests
    * a member is a peer that sent at least one info call and sent anything within a 
    defined timespan (default: 300 sec). If this lunchinator belongs to a group, i.e. the 
    group-setting is not empty, a peer must also belong to our group to be a member.
    
    With a few exception most calls to exchange information about the network or the instance
    are sent to all known peers (structural events). 
    Natural language messages are usually sent to members only. Peers that are in another 
    group drop messages by default. 
    
    All public functions (not starting with _) are thread safe unless the documentation 
    says something else ^^.
    
    """

    def __init__(self):
        """after initializing all variables, the peer information form the lust run is read from a file"""
        self._memberIDs = set()  # of PeerIDs members: peers that sent their info, are active and belong to my group
        self._IP_seen = {}  # last seen timestamps by IP
        self._peer_info = {}  # information of every peer by IP
        self._idToIp = {}  # mapping from ID to a set of IPs
        
        self._groups = set()  # seen group names
        
        self._new_peerIPs = set()  # peers I have to ask for info 
        
        self._lock = loggingMutex("peers", logging=get_settings().get_verbose())
        
        self._initPeersFromFile()  
        
    def finish(self):
        """should be called for a clean shutdown of the program, the peer information will be stored in a file"""
        self._writePeersToFile()
    
    ################ Group Operations #####################
    # no lock -> groups are not removed  
    def getGroups(self):  
        """returns a collection of all lunch groups"""
        return self._groups
    
    def addGroup(self, group_name):
        """adds a new group 
        (done by the lunch server thread)"""
        if group_name not in self._groups:
            self._groups.add(group_name)
            # TODO: what was the second parameter supposed to be?
            get_notification_center().emitGroupAppended(group_name, self._groups)
            
    
    ################ IP Timestamp Operations #####################
    # no locks needed: timeouts are not removed
    def seenIP(self, ip):
        """record that there was contact with the given IP just now
        needed for cleanup of peer data
        (done by the lunch server thread)"""
        self._IP_seen[ip] = time() 
        
    def getIPLastSeen(self, ip):
        """returns a timestamp of the last contact with that IP"""
        if ip in self._IP_seen:
            return self._IP_seen[ip]
        return None  
    
    # here we need a lock
    def getIDLastSeen(self, pID):
        """returns a timestamp of the last contact with the peer given by its ID"""
        with self._lock:
            if pID in self._idToIp:
                return max([self.getIPLastSeen(ip) for ip in self._idToIp[pID]])
            else:
                return -1
    
    ################ Member Operations #####################
    def addMemberByIP(self, ip):
        """promote a peer to member - the peer must be known"""
        with self._lock:
            if ip in self._peer_info:
                self._addMember(self._peer_info[ip][u"ID"])
            else:
                log_warning("Tried to promote peer with IP %s to member, but I do not know that peer")
    
    def isMemberByIP(self, ip):
        """check if the given IP belongs to a member"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u"ID"] in self._memberIDs
            else:
                return False
            
    def removeMembersByIP(self, toRemove=None):
        """remove members identified by their IPs, if toRemove is None, all members are removed"""
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
        """returns the IPs of all members"""
        with self._lock:
            return [ self._idToIp[ID] for ID in self._memberIDs ]            
        
    def getMembers(self):
        """returns the IDs of all members"""
        return deepcopy(self._memberIDs)    
    
    def getReadyMembers(self):
        """returns a list of IDs of all members that are ready for lunch"""
        with self._lock:
            return set([x for x in self._memberIDs if self._checkInfoForReady(self._getPeerInfoByID(x)) ])

    def _addMember(self, pID):
        if pID not in self._memberIDs:
            log_debug("Peer %s is a member" % pID) 
            self._memberIDs.add(pID)           
            get_notification_center().emitMemberAppended(pID, deepcopy(self._getPeerInfoByID(pID)))
        else:  # something may have changed for the member data
            get_notification_center().emitMemberUpdated(pID, deepcopy(self._getPeerInfoByID(pID)))
            
    def _removeMember(self, pID):
        if pID in self._memberIDs:
            self._memberIDs.remove(pID)
            get_notification_center().emitMemberRemoved(pID)  
    
     
    
    
    ################ Peer Operations #####################            
    def removePeerIPs(self, toRemove):
        """removes the given IPs and drops information collected about these peers.
        If a peer is registered under multiple IPs and not all are removed its data 
        is not dropped."""
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        with self._lock:
            for ip in toRemove:
                if ip in self._peer_info:
                    pID = self._peer_info.pop(ip)[u"ID"]
                    self._removePeerIPfromID(pID, ip)
                     
                        
    def getPeerInfoByIP(self, ip):
        """Returns the info dictionary for a peer identified by its IP 
        or None if the ID is unknown"""
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
        """Returns the group of a peer identified by its IP"""
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
    
    def getPeerNameNoLock(self, pID):
        """unlocked version, DO NOT use unless you know what you are doing"""
        i = self._getPeerInfoByID(pID)
        if i:
            return i[u'name']
        return None
    
    def getPeerNameByIP(self, ip):
        """Returns the name of the peer identified by its IP or None if not a peer"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u'name']
        return None 
    
    def getPeerID(self, ip):
        """Returns the ID of a peer that was sent from the given IP"""
        with self._lock:
            if ip in self._peer_info:
                return self._peer_info[ip][u'ID']
        return None
    
    def getPeerIDNoLock(self, ip):
        """unlocked version, DO NOT use unless you know what you are doing"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'ID']
        return None
    
    def getPeerIDsByName(self, peerName):
        """Returns a list of peer IDs of peers with the given name."""
        names = []
        with self._lock:
            for anID, aDict in self._peer_info.iteritems():
                if u"name" in aDict and aDict[u"name"] == peerName:
                    names.append(anID)
        return names
    
    def getPeerIPs(self, pID=None):
        """returns the IPs of a peer or of all peers if pID==None"""
        if pID == None:
            return self._peer_info.keys()
        with self._lock:
            if pID in self._idToIp:
                return set(self._idToIp[pID])
        return []
    
    def getPeerIPsNoLock(self, pID=None):
        """unlocked version, DO NOT use unless you know what you are doing"""
        if pID == None:
            return self._peer_info.keys()
        if pID in self._idToIp:
            return set(self._idToIp[pID])
        return [] 
    
    def isPeerReadyByIP(self, ip):
        """returns true if the peer identified by the given IP is ready for lunch"""
        with self._lock:
            if ip in self._peer_info:
                return self._checkInfoForReady(self._peer_info[ip])
        return False
    
    def createPeerByIP(self, ip, info={}):  
        """adds a peer for that IP and creates a valid info object for this peer.
        If the info dictionary does not contain ID, name and group, ID and name 
        are defaulted to the IP and the group is left empty.
        Within the next seconds a request for info will be sent to this IP."""
        
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
        """The info for the peer that contacted this lunchinator from the given IP 
        will be updated with the data given by newInfo - afterwards a signal is emitted 
        and the group membership is checked in case this lunchinator is in a group.
        If the peer is in the same group it will be promoted to member, otherwise it 
        will be removed from the list of members. Further signals are emitted if the peer
        is in a group we do not know yet and for member append/remove/update"""
        with self._lock:    
            if ip in self._new_peerIPs:
                self._new_peerIPs.remove(ip)
            oldPID = self._peer_info[ip][u"ID"]
            if newInfo == self._peer_info[ip]:
                log_debug("%s sent his info but nothing new"%ip)
                return
            self._peer_info[ip].update(newInfo)
            newPID = self._peer_info[ip][u"ID"]
            
            if newPID != oldPID:
                self._removePeerIPfromID(oldPID, ip)
                self._addPeerIPtoID(newPID, ip)
            else:
                # TODO(Hannes) this info is now the most recent for this ID
                get_notification_center().emitPeerUpdated(newPID, deepcopy(self._peer_info[ip]))
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
                # copy before changing members-list, cannot change while iterating
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
        """Returns all data stored in the peerInfo dict -> all data on all peers"""
        return deepcopy(self._peer_info)
            
    def getNewPeerIPs(self):
        """Returns the list of peers this lunchinator instance has not had contact with"""
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
            get_notification_center().emitPeerRemoved(pID)  
     
    def _addPeerIPtoID(self, pID, ip):       
        if pID not in self._idToIp:
            self._idToIp[pID] = set()
            self._idToIp[pID].add(ip)   
            get_notification_center().emitPeerAppended(pID, deepcopy(self._peer_info[ip]))
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
                    line = line.split("\t", 1)
                    hostn = line[0].strip()
                    peerId = unicode(hostn)
                    pInfo = None
                    if len(line) > 1:
                        try:
                            pInfo = json.loads(line[1])
                            if type(pInfo) != dict:
                                raise
                        except Exception, e:
                            log_debug("Was not able to extract peerInfo from peersFile -> maybe old format: " + str(e))
                            peerId = unicode(line[1].strip())
                        
                    if not hostn:
                        continue
                    try:
                        ip = unicode(socket.gethostbyname(hostn))
                        if pInfo:
                            self.createPeerByIP(ip, pInfo)
                        else:
                            self.createPeerByIP(ip, {u"name":unicode(hostn), u"ID":peerId})
                    except socket.error, e:
                        log_warning("cannot find host specified in members_file by %s with name %s" % (p_file, hostn))
    
    def _writePeersToFile(self):
        try:
            if len(self._peer_info) > 1:
                with codecs.open(get_settings().get_peers_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    with self._lock:
                        for ip, info in self._peer_info.iteritems():
                            f.write(u"%s\t%s\n" % (ip, json.dumps(info)))
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
