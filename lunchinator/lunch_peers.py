import os, codecs, socket
from copy import deepcopy
from time import time
from lunchinator import get_settings, get_notification_center
from lunchinator.utilities import getTimeDifference
from lunchinator.logging_mutex import loggingMutex
from lunchinator.peer_names import PeerNames
from lunchinator.log import newLogger, loggingFunc
        
def peerGetter(needsID=False):
    def peerDecorator(func):
        if needsID:
            def newGetter(self, pID=None, pIP=None, lock=True):
                if lock:
                    self._lock.acquire()
                try:
                    if not pID and pIP:
                        if pIP in self._peer_info:
                            pID = self._peer_info[pIP][LunchPeers.PEER_ID_KEY]
                    return func(self, pID)
                finally:
                    if lock:
                        self._lock.release()
        else:
            def newGetter(self, pID=None, pIP=None, lock=True):
                if lock:
                    self._lock.acquire()
                try:
                    if not pIP and pID:
                        if pID in self._idToIp:
                            pIP = self._idToIp[pID][-1]
                        else:
                            pIP = None
                    return func(self, pIP)
                finally:
                    if lock:
                        self._lock.release()
        return newGetter
    return peerDecorator
        
class LunchPeers(object):    
    """This class holds information about all peers known to the lunchinator,
    Terminology:
    * a peer is anyone who sent an info dictionary to this lunchinator.
    a peer can either be identified by its IP and additionally by any ID it told us
    (usually an UUID). This way a peer that changed its IP (e.g. because of switching 
    between LAN and WLAN, or because of DHCP) can be recognised later. If no ID was 
    sent, the ID is the IP. Peers are removed after a defined timeout (default: 300 sec 
    after the last contact or within approx. a minute if they are not reacting to our 
    requests)
    * a candidate is an IP / a hostname that once was a peer. An append-only
    list of candidates is maintained and used on startup to quickly reconnect with 
    all other Lunchinators in the network.
    * a member is a peer that belongs to the same group as this Lunchinator.
    Lunchinators with an empty group form their own group that does not
    communicate with other Lunchinators.
    
    With a few exception most calls to exchange information about the network or the instance
    are sent to all known peers (structural events). 
    Natural language messages are usually sent to members only. Peers that are in another 
    group drop messages by default. 
    
    All public functions (not starting with _) are thread safe unless the documentation 
    says something else ^^.
    
    """
    
    """Default Info Dict keys"""
    PEER_ID_KEY = u"ID"
    PEER_NAME_KEY = u"name"
    GROUP_KEY = u"group"
    AVATAR_KEY = u"avatar"
    NEXT_LUNCH_BEGIN_KEY = u"next_lunch_begin"
    NEXT_LUNCH_END_KEY = u"next_lunch_end"
    APPLICATION_VERSION_KEY = u"version"
    APPLICATION_COMMIT_COUNT_KEY = u"version_commit_count"
    PLATFORM_KEY = u"platform"

    def __init__(self):
        """after initializing all variables, the peer information form the lust run is read from a file"""
        self.logger = newLogger("Peers")
        self._potentialPeers = set() # set containing data from lunch_peers.cfg 
        self._memberIDs = set()  # of PeerIDs members: peers that sent their info, are active and belong to my group
        self._IP_seen = {}  # last seen timestamps by IP
        self._peer_info = {}  # information of every peer by IP
        self._idToIp = {}  # mapping from ID to a set of IPs
        
        self._groups = set()  # seen group names
        
        self._lock = loggingMutex("peers", logging=get_settings().get_verbose())
        
        if get_settings().get_plugins_enabled():
            self._peerNames = PeerNames()
        else:
            self._peerNames = None 
        
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
        
        # check if ip is the last one in the ip list of the corresponding peer
        with self._lock:
            pID = self.getPeerID(pIP=ip, lock=False)
            if pID in self._idToIp:
                ips = self._idToIp[pID]
                if ips[-1] != ip:
                    # move last seen to the end of the list
                    try:
                        idx = ips.index(ip)
                        ips[idx], ips[-1] = ips[-1], ips[idx]
                    except ValueError:
                        self.logger.error("IP %s of peer %s not in _idToIP", ip, pID)
        
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
                return self._idToIp[pID][-1]
            else:
                return -1
    
    ################ Member Operations #####################
    
    def removeMembersByIP(self, toRemove=None):
        """remove members identified by their IPs, if toRemove is None, all members are removed"""
        with self._lock:
            if toRemove == None:
                mem = deepcopy(self._memberIDs)
                for mID in mem:
                    self._removeMember(mID)
                return
                
            if type(toRemove) != set:
                toRemove = set(toRemove)
                
            for ip in toRemove:
                if ip in self._peer_info:
                    self._removeMember(self._peer_info[ip][self.PEER_ID_KEY])
    
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
            return set([x for x in self._memberIDs if self._checkInfoForReady(self.getPeerInfo(pID=x, lock=False)) ])

    def _addMember(self, pID):
        if pID not in self._memberIDs:
            self.logger.debug("Peer %s is a member", pID) 
            self._memberIDs.add(pID)           
            get_notification_center().emitMemberAppended(pID, deepcopy(self.getPeerInfo(pID=pID, lock=False)))
        else:  # something may have changed for the member data
            get_notification_center().emitMemberUpdated(pID, deepcopy(self.getPeerInfo(pID=pID, lock=False)))
            
    def _removeMember(self, pID):
        if pID in self._memberIDs:
            self._memberIDs.remove(pID)
            get_notification_center().emitMemberRemoved(pID)  
    
    ################ Peer Operations #####################    
    def removePeer(self, pID):
        with self._lock:
            if pID not in self._idToIp:
                return
            pIPs = self._idToIp.pop(pID)
            self._removeMember(pID)
            for pIP in pIPs:
                self._peer_info.pop(pIP)
        
        get_notification_center().emitPeerRemoved(pID)
                
    def removePeerIPs(self, toRemove):
        """removes the given IPs and drops information collected about these peers.
        If a peer is registered under multiple IPs and not all are removed its data 
        is not dropped."""
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        with self._lock:
            for ip in toRemove:
                if ip in self._peer_info:
                    pID = self._peer_info.pop(ip)[self.PEER_ID_KEY]
                    self._removePeerIPfromID(pID, ip)
                     
    ########### Getters for peer / member information ##############
    # All of the following public methods take keyword arguments:
    #  pID -- Identify peer via peer ID
    #  pIP -- Identify peer via IP
    #  lock -- If false, the getter won't be locked
    # If a single argument is given, it is interpreted as a peer ID.  
    
    @peerGetter(needsID=True)
    def isMember(self, pID):
        """check if the given IP/ID belongs to a member"""
        return pID in self._memberIDs
    
    @peerGetter(needsID=True)
    def isMe(self, pID):
        """check if the given IP/ID belongs to a member"""
        return pID == get_settings().get_ID()

    @peerGetter()
    def getPeerInfo(self, ip):
        """Returns the info dictionary for a peer
        
        Returns the info dictionary for the peer or None if the IP/ID
        is unknown.
        """
        if ip in self._peer_info:
            return deepcopy(self._peer_info[ip])
        else:
            return None
    
    @peerGetter()
    def getPeerGroup(self, ip):
        """Returns the group of a peer"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'group']
        return None   
    
    
    @peerGetter()
    def getPeerCommitCount(self, ip):
        """Returns the internal version of a peer"""
        if ip in self._peer_info:
            try:
                return int(self._peer_info[ip][u'version_commit_count'])
            except:
                self.logger.debug("Commit Count is not an Integer")
                return None
        return None   
    
    @peerGetter()
    def getRealPeerName(self, ip):
        """Returns the real name of the peer, as provided by its info dict."""
        i = self.getPeerInfo(pIP=ip, lock=False)
        if i:
            return i[u'name']
        return u"<unknown>"

    @peerGetter(needsID=True)
    def getDisplayedPeerName(self, peerID):
        """Returns the displayed peer name for a given peer ID.
        
        The displayed name is the last known peer name in the
        info dict of the given peer if no custom name was specified.
        Else, the custom name is returned.
        """
        if self._peerNames != None:
            try:
                return self._peerNames.getDisplayedPeerName(peerID)
            except:
                self.logger.exception("Error obtaining displayed peer name")
        # Fall back to peer info dictionary if peer names are not available
        return self.getRealPeerName(pID=peerID, lock=False)
        
    @peerGetter(needsID=True)
    def hasCustomPeerName(self, peerID):
        """Returns True if the peer has a custom peer name."""
        if self._peerNames == None:
            return False
        
        return self._peerNames.hasCustomName(peerID)
        
    @peerGetter()    
    def getPeerID(self, ip):
        """Returns the ID of a peer that was sent from the given IP"""
        if ip in self._peer_info:
            return self._peer_info[ip][u'ID']
        return None

    @peerGetter(needsID=True)
    def isPeerID(self, pID):
        return pID in self._idToIp
    
    @peerGetter(needsID=True)
    def getPeerIPs(self, pID):
        """returns the IPs of a peer or of all peers if pID==None"""
        if pID == None:
            return self._peer_info.keys()
        
        if pID in self._idToIp:
            return set(self._idToIp[pID])
        return []
    
    @peerGetter(needsID=True)
    def getFirstPeerIP(self, pID):
        """returns the first IP of a peer or of all peers if pID==None
        @return: set
        """
        if pID == None:
            return [ips[-1] for ips in self._idToIp.values()]
        
        if pID in self._idToIp:
            return [self._idToIp[pID][-1]]
        return []
    
    @peerGetter()
    def isPeerReady(self, ip):
        """returns true if the peer identified by the given IP is ready for lunch"""
        if ip in self._peer_info:
            return self._checkInfoForReady(self._peer_info[ip])
        return False    
    
    @peerGetter()
    def isPeerReadinessKnown(self, ip):
        """returns True if there is a valid lunch time interval for the peer"""
        if ip in self._peer_info:
            p_info = self._peer_info[ip]
            if p_info and p_info.has_key(self.NEXT_LUNCH_BEGIN_KEY) and p_info.has_key(self.NEXT_LUNCH_END_KEY):
                diff = getTimeDifference(p_info[self.NEXT_LUNCH_BEGIN_KEY], p_info[self.NEXT_LUNCH_END_KEY], self.logger)
                if diff != None:
                    # valid format
                    return True
        return False
    
    @peerGetter()
    def getPeerAvatarFile(self, ip):
        """Returns the path to a peer's avatar file, if it exists.

        The method returns None if the peer does not have an avatar or
        the file does not exist.
        """
        peerInfo = self.getPeerInfo(pIP=ip, lock=False)
        if peerInfo != None and self.AVATAR_KEY in peerInfo and peerInfo[self.AVATAR_KEY]:
            avatarFile = os.path.join(get_settings().get_avatar_dir(), peerInfo[self.AVATAR_KEY])
            if os.path.isfile(avatarFile):
                return avatarFile
        return None
    
    @peerGetter()
    def getAvatarOutdated(self, ip):
        """Returns True if the peer has an avatar but we don't have it"""
        peerInfo = self.getPeerInfo(pIP=ip, lock=False)
        if peerInfo != None and self.AVATAR_KEY in peerInfo and peerInfo[self.AVATAR_KEY]:
            avatarFile = os.path.join(get_settings().get_avatar_dir(), peerInfo[self.AVATAR_KEY])
            return not os.path.exists(avatarFile)
        # doesn't have avatar
        return False
        
    ############### Additional getters ##################
    
    def _checkInfoForReady(self, p_info):
        if p_info and p_info.has_key(self.NEXT_LUNCH_BEGIN_KEY) and p_info.has_key(self.NEXT_LUNCH_END_KEY):
            diff = getTimeDifference(p_info[self.NEXT_LUNCH_BEGIN_KEY], p_info[self.NEXT_LUNCH_END_KEY], self.logger)
            if diff == None:
                # illegal format, just assume ready
                return True
            return diff > 0
        else:
            # no lunch time information (only happening with very old lunchinators), assume ready
            return True
        
    def getPeerIDsByName(self, peerName, sensitive=True):
        """Returns a list of peer IDs of peers with the given name.
        
        The name can either be a peer's real name or a custom name.
        """
        if self._peerNames != None:
            return [peerID for peerID in self._peerNames.iterPeerIDsByName(peerName, sensitive)]
        else:
            if not sensitive:
                peerName = peerName.lower()
            names = []
            with self._lock:
                if sensitive:
                    for anID, aDict in self._peer_info.iteritems():
                        if self.PEER_NAME_KEY in aDict and aDict[self.PEER_NAME_KEY] == peerName:
                            names.append(anID)
                else:
                    for anID, aDict in self._peer_info.iteritems():
                        if self.PEER_NAME_KEY in aDict and aDict[self.PEER_NAME_KEY].lower() == peerName:
                            names.append(anID)
            return names
    
    def getPeers(self):
        """returns the IDs of all peers"""
        with self._lock:
            return list(self._idToIp.keys())
    
    def getAllKnownPeerIDs(self):
        """Returns the IDs of all peers ever known."""
        with self._lock:
            return self._peerNames.getAllPeerIDs()
    
    def getPeerInfoDict(self):
        """Returns all data stored in the peerInfo dict -> all data on all peers"""
        return deepcopy(self._peer_info)
    
    ############# Setters #################
    
    def setCustomPeerName(self, peerID, customName):
        """This method might occasionally raise an exception"""
        if self.isMe(pID=peerID):
            # special case: it doesn't make sense to use the custom name for myself
            get_settings().set_user_name(customName)
        else:
            with self._lock:
                infoDict = self.getPeerInfo(pID=peerID, lock=False)
                self._peerNames.setCustomName(peerID, customName, infoDict)
    
    ############# Methods for initialization and update ################
    
    def _createPeerByIP(self, ip, info):  
        """adds a peer for that IP"""
        self.logger.info("new peer: %s", ip)
        self._peer_info[ip] = info
        pID = self._peer_info[ip][self.PEER_ID_KEY]
        self._addPeerIPtoID(pID, ip)
            
        if not self._IP_seen.has_key(ip):
            self._IP_seen[ip] = -1
            
    def updatePeerInfoByIP(self, ip, newInfo):  
        """Adds a peer info dict to an IP
        
        The info for the peer that contacted this lunchinator from the given IP 
        will be updated with the data given by newInfo. If the IP is unknown, the
        IP will be added as a new peer. Otherwise, a signal is emitted 
        and the group membership is checked in case this lunchinator is in a group.
        If the peer is in the same group it will be promoted to member, otherwise it 
        will be removed from the list of members. Further signals are emitted if the peer
        is in a group we do not know yet and for member append/remove/update
        
        @type ip: unicode
        @type newInfo: dict 
        """
        # Make sure the required keys are in the dict
        if u'group' not in newInfo:
            newInfo[u'group'] = u""
        if u'name' not in newInfo:
            newInfo[self.PEER_NAME_KEY] = ip
        if self.PEER_ID_KEY not in newInfo:
            newInfo[self.PEER_ID_KEY] = ip
    
        newPID = newInfo[self.PEER_ID_KEY]
    
        with self._lock:
            if ip in self._peer_info and self._peer_info[ip][self.PEER_ID_KEY] != newPID:
                # IP has a new ID, assume different peer -> old peer does not use IP any more
                self._removePeerIPfromID(self._peer_info[ip][self.PEER_ID_KEY], ip)
                del self._peer_info[ip]
            
            if ip not in self._peer_info and newPID not in self._idToIp:
                # this is a new peer
                self._createPeerByIP(ip, newInfo)
            else:
                # this is either an update to an existing IP or a new IP for an existing peer
                if ip in self._peer_info and newPID in self._idToIp:
                    # this is an update
                    existing_info = self._peer_info[ip]
                elif ip not in self._peer_info and newPID in self._idToIp:
                    # this is a new IP for an existing peer
                    self.logger.debug("New IP: %s for ID: %s", ip, newPID)
                    existing_info = self._peer_info[self._idToIp[newPID][-1]]
                    self._peer_info[ip] = existing_info
                    self._addPeerIPtoID(newPID, ip)
                elif ip in self._peer_info and newPID not in self._idToIp:
                    # we already know this IP but it is not this peer - should not happen
                    self.logger.error("Something went wrong - ID %s is missing in _idToIp", newPID)
                    return
                    
                old_info = deepcopy(existing_info)
                existing_info.update(newInfo)
                
                removedKeys = set(old_info.keys()) - set(newInfo.keys())
                for key in removedKeys:
                    existing_info.pop(key)
                    
                if old_info != existing_info:
                    if self._peerNames is not None:
                        self._peerNames.addPeerName(newPID, existing_info)
                    get_notification_center().emitPeerUpdated(newPID, deepcopy(existing_info))
                    self.logger.debug("%s has new info: %s; \n update was %s", ip, existing_info, newInfo)
                else:
                    self.logger.debug("%s sent info - without new info", ip)
                    
                if self.AVATAR_KEY in old_info and self.AVATAR_KEY in existing_info and \
                   old_info[self.AVATAR_KEY] != existing_info[self.AVATAR_KEY] and \
                   not self.getAvatarOutdated(pIP=ip, lock=False):
                    # avatar changed but we already have the picture
                    get_notification_center().emitAvatarChanged(newPID, deepcopy(existing_info[self.AVATAR_KEY]))
            
            own_group = get_settings().get_group()
            
            if self._peer_info[ip][self.GROUP_KEY] == own_group:
                self._addMember(newPID)
                self.addGroup(self._peer_info[ip][self.GROUP_KEY])
            else:
                self._removeMember(newPID)
                
    def removeInactive(self):
        """
        peers that haven't been seen for <peerTimeout> seconds are removed
        and a PeerRemoved notification is sent. If a removed peer was a
        member, a MemberRemoved notification is sent, too.
        """
        
        self.logger.debug("Removing inactive peers")      
        try:            
            with self._lock:
                for ip in self._IP_seen:
                    if ip in self._peer_info and time() - self._IP_seen[ip] > get_settings().get_peer_timeout():
                        pID = self._peer_info[ip][self.PEER_ID_KEY]
                        self._removePeerIPfromID(pID, ip)
                        del self._peer_info[ip]
        except:
            self.logger.exception("Something went wrong while trying to clean up the list of peers")
             
    def _removePeerIPfromID(self, pID, ip):   
        self.logger.debug("Removing %s from ID: %s", ip, pID)
        self._idToIp[pID].remove(ip)
        
        if 0 == len(self._idToIp[pID]):
            # no IP associated with that ID -> remove peer
            #remove member first
            self._removeMember(pID)
            self._idToIp.pop(pID)
            get_notification_center().emitPeerRemoved(pID)
        else:
            existing_ip = self._idToIp[pID][0]
            get_notification_center().emitPeerUpdated(pID, deepcopy(self._peer_info[existing_ip]))
     
    def _addPeerIPtoID(self, pID, ip):       
        if pID not in self._idToIp:
            self._idToIp[pID] = [ip]
            if self._peerNames is not None:
                self._peerNames.addPeerName(pID, self._peer_info[ip])
            get_notification_center().emitPeerAppended(pID, deepcopy(self._peer_info[ip]))
        else:
            # last one is last seen one
            self._idToIp[pID].append(ip)
            #workaround to get the IP over to the slots
            cp = deepcopy(self._peer_info[ip])
            cp["triggerIP"] = ip
            get_notification_center().emitPeerUpdated(pID, cp)
            
    def initPeersFromFile(self):
        """Initializes peer IPs from file and returns a list of IPs
        to request info from."""
        p_file = get_settings().get_peers_file() if os.path.exists(get_settings().get_peers_file()) else get_settings().get_members_file()
        
        peerIPs = []
        #TODO change AF_INET when going to v6
        #TODO for Mac: incorporate search domains somehow?
        ownIPs = set()
        try:
            ownIPs = set(i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
        except socket.error:
            self.logger.warning("socket error trying to obtain own IP")
        if not ownIPs:
            self.logger.warning("Didn't find IPs for ourselves")
        for ip in ownIPs:
            peerIPs.append(ip)
        if os.path.exists(p_file):
            with codecs.open(p_file, 'r', 'utf-8') as f:    
                for line in f.readlines():
                    line = line.split("\t", 1)
                    hostn = line[0].strip()
                    if not hostn:
                        continue
                    try:
                        self._potentialPeers.add(hostn)
                        #TODO change AF_INET when going to v6
                        for ip in set(i[4][0] for i in socket.getaddrinfo(hostn, None, socket.AF_INET)):
                            peerIPs.append(ip)
                    except socket.error:
                        self.logger.debug("cannot find host specified in members_file by %s with name %s", p_file, hostn)
        return peerIPs
    
    def _writePeersToFile(self):
        try:
            with self._lock:
                for ip in self._peer_info:
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = ip
                    self._potentialPeers.add(hostname)
                        
                with codecs.open(get_settings().get_peers_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    f.write(u"\n".join(sorted(self._potentialPeers)))
        except:
            self.logger.exception("Could not write peers to %s", get_settings().get_peers_file())
            
    @loggingFunc
    def _alertIfIPnotMyself(self, newPID, peerInfo):
        """ alert if ID is mine but ip is not from my machine
        
        this function has to be called from the main thread
        
        @return: True if that's my ID from another machine
        
        @type newPID: unicode
        @type peerInfo: dict
        @rtype: bool
        """
        
        if not peerInfo.has_key("triggerIP") or newPID != get_settings().get_ID():
            #that's not me!
            return False
        
        ip = peerInfo["triggerIP"]
        myname = socket.gethostname() #socket.getfqdn(socket.gethostname())
        othername = ""
        try:
            othername = socket.gethostbyaddr(ip)[0]
        except:
            self.logger.warning("Another IP (%s) contacted me with my ID, I can't find it's hostname..., won't do anything now."%ip)
            return False
        
        #make sure, we only check the hostname, not the fqdn
        i = myname.find('.')
        if i != -1:
            myname = myname[:i]
        i = othername.find('.')
        if i != -1:
            othername = othername[:i]
    
        if myname==othername:
            #that seems to be me from another, maybe on a second
            #network interface
            return False        
        
        if othername in get_settings().get_multiple_machines_allowed():
            #he is allowed to do that
            return False
        
        #that seems to be coming from an unknown machine and has to be reported
        from lunchinator import lunchinator_has_gui
        msg ="Another lunchinator on the network (%s: %s)"%( ip, othername) + \
              "is identifying itself with your (%s) ID. "%myname +\
              "It will get all messages you get, also private ones!\n"
              
        if lunchinator_has_gui():
            msg += "If this is not what you want, you should create a new ID immediately."
            from PyQt4.QtGui import QMessageBox, QPushButton
            msgBox = QMessageBox(None)
#             msgBox.setIcon(QMessageBox.Warning)
#             msgBox.setWindowTitle("Another Lunchinator with your ID detected")
            msgBox.setText(msg)
            msgBox.addButton(QPushButton('Create New ID'), QMessageBox.AcceptRole)
            msgBox.addButton(QPushButton('Ignore'), QMessageBox.NoRole)
            msgBox.addButton(QPushButton('Allow host to get my messages'), QMessageBox.RejectRole)
            ret = msgBox.exec_();
            if ret==QMessageBox.AcceptRole:
                get_settings().generate_ID()
            elif ret!=QMessageBox.NoRole:
                get_settings().add_multiple_machines_allowed(othername)
        else:
            msg += "If you are sure that this is right you can set "+\
              "multiple_machines_allowed = %s in your settings.cfg \n"%ip+\
              "Otherwise you should create a new ID immediately.\n"
            self.logger.critical(msg)
        return True
        
    def __len__(self):
        return len(self._idToIp)    
        
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
    
    def __iter__(self):
        return self._idToIp.iterkeys().__iter__()
