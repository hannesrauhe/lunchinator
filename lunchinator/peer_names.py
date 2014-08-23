from lunchinator import get_notification_center, convert_string,\
    get_db_connection
from lunchinator.log import newLogger, loggingFunc
        
class PeerNames(object):
    _DB_VERSION_INITIAL = 0
    _DB_VERSION_CURRENT = _DB_VERSION_INITIAL
    
    def __init__(self, lock):
        self.logger = newLogger("Peer Names")
        self._lock = lock
        self._db, plugin_type = get_db_connection(self.logger)
        self._peerNameCache = {} # peer ID -> (peer name, custom name)
        
        if plugin_type != "SQLite Connection":
            self.logger.warning("Your standard connection is not of type SQLite." + \
                "Loading peer names from another type is experimental.")
        
        if not self._db.existsTable("CORE_PEER_NAME_VERSION"):
            self._db.execute("CREATE TABLE CORE_PEER_NAME_VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO CORE_PEER_NAME_VERSION(VERSION) VALUES(?)", self._DB_VERSION_CURRENT)
                        
        if not self._db.existsTable("CORE_PEER_NAMES"):
            self._db.execute("CREATE TABLE CORE_PEER_NAMES(PEER_ID TEXT PRIMARY KEY NOT NULL, PEER_NAME TEXT NOT NULL, CUSTOM_NAME TEXT)")
            if self._db.existsTable("CORE_MESSAGE_PEER_NAMES"):
                # copy from message peer names
                self._db.execute("INSERT INTO CORE_PEER_NAMES SELECT PEER_ID, PEER_NAME, NULL FROM CORE_MESSAGE_PEER_NAMES")
                self._db.execute("DROP TABLE CORE_MESSAGE_PEER_NAMES")
            
        get_notification_center().connectPeerAppended(self._addPeerName)
        get_notification_center().connectPeerUpdated(self._addPeerName)

    def _getDBVersion(self):
        return self._db.query("SELECT VERSION FROM CORE_PEER_NAME_VERSION")[0][0]
    
    def finish(self):
        get_notification_center().disconnectPeerAppended(self._addPeerName)
        get_notification_center().disconnectPeerUpdated(self._addPeerName)
        
    @loggingFunc
    def _addPeerName(self, peerID, peerInfo):
        peerID = convert_string(peerID)
        with self._lock:
            self._checkCache(peerID)
        oldName, customName = self._peerNameCache[peerID]
        changed = False
        
        newName = peerInfo[u"name"]
        if oldName == None:
            # need to insert
            self._db.execute("INSERT INTO CORE_PEER_NAMES VALUES(?, ?, NULL)", peerID, newName)
            get_notification_center().emitPeerNameAdded(peerID, newName)
        elif oldName != newName:
            # need to update
            self._db.execute("UPDATE CORE_PEER_NAMES SET PEER_NAME = ? WHERE PEER_ID = ?", newName, peerID)
            changed=True
        else:
            newName = None
        
        if newName != None:
            with self._lock:
                self._peerNameCache[peerID] = (newName, customName)
            # if there is a custom name, a change in the info dict does not change the displayed name
            if changed and not customName:
                get_notification_center().emitDisplayedPeerNameChanged(peerID, newName, peerInfo)
            
    def _getPeerNameFromDB(self, peerID):
        # TODO bulk loading if necessary
        res = self._db.query("SELECT PEER_NAME, CUSTOM_NAME FROM CORE_PEER_NAMES WHERE PEER_ID = ?", peerID)
        if len(res) > 0:
            return res[0][0], res[0][1]
        return None, None
    
    def _checkCache(self, peerID):
        if peerID not in self._peerNameCache:
            peerName, customName = self._getPeerNameFromDB(peerID)
            self._peerNameCache[peerID] = (peerName, customName)
    
    def setCustomName(self, peerID, customName, infoDict=None):
        """Called from lunch_peers, no locking"""
        self._checkCache(peerID)
        peerName, oldCustomName = self._peerNameCache[peerID]
        if peerName == None:
            self.logger.error("Trying to specify custom name for unknown peer")
            return
        self._peerNameCache[peerID] = (peerName, customName)
            
        if oldCustomName != customName:
            self._db.execute("UPDATE CORE_PEER_NAMES SET CUSTOM_NAME = ? WHERE PEER_ID = ?", customName, peerID)
            get_notification_center().emitDisplayedPeerNameChanged(peerID, self.getDisplayedPeerName(peerID), infoDict)
    
    def hasCustomName(self, peerID):
        """called from lunch_peers, no locking"""
        self._checkCache(peerID)
        _peerName, customName = self._peerNameCache[peerID]
        return customName != None
    
    def getDisplayedPeerName(self, peerID):
        """Returns the displayed peer name for a given peer ID.
        
        The displayed name is the last known peer name in the
        info dict of the given peer if no custom name was specified.
        Else, the custom name is returned.
        
        This method does not lock; use get_peers().getDisplayedPeerName
        instead
        """        
        self._checkCache(peerID)
        peerName, customName = self._peerNameCache[peerID]
        if customName:
            return customName
        else:
            return peerName

    def iterPeerIDsByName(self, searchedName):
        """Iterates over peer IDs with a given name.
        
        The name can either be a real name or a custom name.
        This method does not block, use get_peers().getPeerIDsByName instead.
        """
        for peerID, aTuple in self._peerNameCache.iteritems():
            peerName, customName = aTuple
            if peerName == searchedName or customName == searchedName:
                yield peerID
                
    def getAllPeerIDs(self):
        """Returns IDs of all peers ever known.
        
        This method does not block, use get_peers().getAllKnownPeerIDs()
        instead."""
        
        return [row[0] for row in self._db.query("SELECT DISTINCT PEER_ID FROM CORE_PEER_NAMES")]
        