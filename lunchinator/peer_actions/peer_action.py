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
    
    def performAction(self, peerID, peerInfo, parentWidget):
        """Called when the action is performed on some peer."""
        pass
    
    def peerMustBeOnline(self):
        """If True (default), peer action will not apply to offline peers.
        
        If this method returns False and a peer action list is requested
        for a peer that is currently not online (has no peer info), the
        peer action will still be displayed.
        """
        return True
    
    def appliesToPeer(self, _peerID, _peerInfo):
        """Override this method if the action only applies to specific peers."""
        return True
    
    def getTimeout(self):
        """Returns the time in seconds until the action times out.
        
        If this method returns a positive number, the confirmation dialog
        on the receiver side will time out after the given number of
        seconds.
        """
        return None
    
    def getMessagePrefix(self):
        """Returns the prefix of the message sent to other peers.
        
        For example, if the action sends HELO_XX {...} to the other peer,
        this method has to return XX.
        By default, if this method does not return None, this action will
        added to the privacy settings. Change this behavior by overriding
        hasPrivacySetttings().
        """
        return None
    
    def hasPrivacySettings(self):
        """Returns whether or not this action has privacy settings.
        
        By default, a PeerAction has privacy settings if it is registered
        to a message prefix. See getMessagePrefix().
        """
        return self.getMessagePrefix() is not None
    
    def getPrivacyCategories(self):
        """Provide more fine-grained privacy settings.
        
        If the peer action sends messages of different types, this method
        can return a list of these types to provide more fine-grained
        privacy settings. This method is called each time the privacy
        settings panel for this peer action is refreshed.
        """
        return None
    
    def hasPrivacyCategory(self, category):
        """Returns True if the given category is supported.
        
        If this method returns False, the action will always be blocked.
        """
        return category in self.getPrivacyCategories()
    
    def getCategoryIcon(self, _category):
        """Returns a QIcon for a given category name."""
        return None
    
    def hasCategories(self):
        """Must return True if getPrivacyCategories returns a list of categories."""
        return False
    
    def preProcessMessageData(self, msgData):
        """Allows the peer action to pre-process the message data."""
        return msgData
    
    def willIgnorePeerAction(self, _msgData):
        """Returns True if the action will not be processed regardless of the privacy settings.
        
        If this method returns True, privacy settings will not be considered.
        The message will be processed as if it was blocked.
        """
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
    
    def getConfirmationMessage(self, _peerID, _peerName, _msgData):
        """Returns the message to be displayed on the confirmation dialog.
        
        If this method returns None, the default message will be
        displayed.
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
        self.logger = pluginObject.logger
        
    def getPrivacyPolicy(self, category=None, categoryPolicy=None):
        """Convenience method to get the privacy policy"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getPolicy(self, category, categoryPolicy=categoryPolicy)
    
    def usesPrivacyCategories(self):
        """Returns True if the current privacy policy uses categories."""
        from lunchinator.privacy import PrivacySettings
        policy = PrivacySettings.get().getPolicy(self, None, categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        return policy == PrivacySettings.POLICY_BY_CATEGORY
        
    def getAskForConfirmation(self, category=None, categoryPolicy=None):
        """Convenience method to get the 'ask for confirmation' state"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getAskForConfirmation(self, category, categoryPolicy=categoryPolicy)
    
    def getPeerState(self, peerID, category=None):
        """Convenience method to get the peer's privacy state"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getPeerState(peerID, self, category)
        
    def getExceptions(self, policy, category=None, categoryPolicy=None):
        """Convenience method to get the exception dict"""
        from lunchinator.privacy import PrivacySettings
        return PrivacySettings.get().getExceptions(self, category, policy, categoryPolicy=categoryPolicy)