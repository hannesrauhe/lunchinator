class PeerAction(object):
    def __init__(self):
        self._pluginName = None
        self._pluginObject = None
    
    ########## REQUIRED ###########
    def getName(self):
        """ Returns the action's displayed name."""
        return None
    
    ########## OPTIONAL ###########
    def getDisplayedName(self, _peerID):
        """Can be used to change the displayed name depending on the context."""
        return self.getName()
    
    def getIcon(self):
        """Returns an icon representing this action."""
        return None
    
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
    
    def getCategoryIcon(self, _category):
        """Returns a QIcon for a given category name."""
        return None
    
    def hasCategories(self):
        """Must return True if getPrivacyCategories returns a list of categories."""
        return False
    
    def getCategoryFromMessage(self, _msgData):
        """Extracts and returns the category of a message.
        
        If getPrivacyCategories() returns a list, this method will be called
        when a message with the message prefix of this peer action is
        received.
        """
        return None
    
    def getDefaultPrivacyPolicy(self):
        """Returns the default privacy mode, see PrivacySettings."""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.POLICY_NOBODY_EX
    
    def getDefaultCategoryPrivacyPolicy(self):
        """Returns the default privacy policy per category.
        
        If there are multiple categories (getPrivaryCategories() returns
        a list), this method specifies the default privacy policy for each
        category.
        """
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.POLICY_NOBODY_EX
    
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
        
    def getPrivacyPolicy(self, category=None):
        """Convenience method to get the privacy policy"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getPolicy(self, category)
        
    def getAskForConfirmation(self, category=None):
        """Convenience method to get the 'ask for confirmation' state"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getAskForConfirmation(self, category)
    
    def getPeerState(self, peerID, category=None):
        """Convenience method to get the peer's privacy state"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getPeerState(peerID, self, category)
        
    def getExceptions(self, policy, category=None):
        """Convenience method to get the exception dict"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getExceptions(self, category, policy)