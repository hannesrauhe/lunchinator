class PeerAction(object):
    def __init__(self):
        self._pluginName = None
        self._pluginObject = None
    
    ########## REQUIRED ###########
    def getName(self):
        """ Returns the action's displayed name."""
        return None
    
    ########## OPTIONAL ###########
    def performAction(self, peerID, peerInfo):
        """Called when the action is performed on some peer."""
        pass
    
    def appliesToPeer(self, _peerID, _peerInfo):
        """Override this method if the action only applies to specific peers."""
        return True
    
    def getMessagePrefix(self):
        """Returns the prefix of the message sent to other peers.
        
        For example, if the action sends HELO_XX {...} to the other peer,
        this method has to return XX.
        If this method does not return None, it will be added to the
        privacy settings.
        """
        return None
    
    def getPrivacyCategories(self):
        """Provide more fine-grained privacy settings.
        
        If the peer action sends messages of different types, this method
        can return a list of these types to provide more fine-grained
        privacy settings. This method is called each time the privacy
        settings panel for this peer action is refreshed.
        """
        return None
    
    ########## DON'T OVERRIDE ##########    
    def getPluginName(self):
        """Returns the parent plugin's name."""
        return self._pluginName
    
    def getPluginObject(self):
        """Returns the parent plugin's plugin object"""
        return self._pluginObject
    
    def setParentPlugin(self, pluginName, pluginObject):
        self._pluginName = pluginName
        self._pluginObject = pluginObject
        