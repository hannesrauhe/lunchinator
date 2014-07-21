import json
from lunchinator import log_exception, get_settings, log_warning, log_error,\
    get_notification_center
from lunchinator.logging_mutex import loggingMutex

def _setter(func):
    def newSetter(self, action, category, *args, **kwargs):
        pluginName = action.getPluginName()
        actionName = action.getName()
        if "applyImmediately" in kwargs:
            applyImmediately = kwargs["applyImmediately"]
            del kwargs["applyImmediately"]
        else:
            applyImmediately = True
        
        if applyImmediately:
            # check if modification is in progress
            settings = self._getActionDict(pluginName, actionName, self._modifications)
            if settings is not None:
                # apply to modified
                func(self, action, category, settingsDict=settings, *args, **kwargs)
            # apply to stored settings
            settings = self._initModification(action, category, actionDictSource=self._settings)
            func(self, action, category, settingsDict=settings, *args, **kwargs)
            
            get_notification_center().emitPrivacySettingsChanged(action.getPluginName(), action.getName())
        else:
            # only add to modification dict
            settings = self._initModification(action, category, actionDictSource=self._modifications)
            func(self, action, category, settingsDict=settings, *args, **kwargs)
    return newSetter

class PrivacySettings(object):
    """Nobody is allowed"""
    POLICY_NOBODY = 0
    """Whitelist mode"""
    POLICY_NOBODY_EX = 1
    """Blacklist mode"""
    POLICY_EVERYBODY_EX = 2
    """Everybody is allowed"""
    POLICY_EVERYBODY = 3
    """Privacy settings per category"""
    POLICY_BY_CATEGORY = 4
    """Special policy for peer exceptions for all categories"""
    POLICY_PEER_EXCEPTION = 5
    
    """The peer is blocked by the current settings"""
    STATE_BLOCKED = 0
    """The peer is free to perform the action by the current settings"""
    STATE_FREE = 1
    """The peer can perform the action but you have to confirm""" 
    STATE_CONFIRM = 2
    """The action has multiple categories and you didn't specify one""" 
    STATE_UNKNOWN = 3
    
    _instance = None
    
    @classmethod
    def get(cls):
        return cls._instance
    
    @classmethod
    def initialize(cls, jsonString):
        cls._instance = PrivacySettings(jsonString)
    
    def __init__(self, jsonString):
        # {plugin name : {action name : {settings}}}
        try:
            self._settings = json.loads(jsonString)
        except ValueError:
            log_exception("Error reading privacy settings from JSON.")
            self._settings = {}
        
        self._modifications = {}
        self._lock = loggingMutex("Privacy Settings", logging=get_settings().get_verbose())
        
    def getJSON(self):
        with self._lock:
            return json.dumps(self._settings)
    
    def _setPeerActionSettings(self, pluginName, actionName, actionSettings):
        if pluginName not in self._settings:
            self._settings[pluginName] = {}
        pluginDict = self._settings[pluginName]
            
        pluginDict[actionName] = actionSettings
    
    def save(self):
        """Saves the current modifications"""
        with self._lock:
            for pluginName, pluginDict in self._modifications.iteritems():
                for actionName, actionDict in pluginDict.iteritems():
                    if u"pol" in actionDict and actionDict[u"pol"] != PrivacySettings.POLICY_BY_CATEGORY:
                        # don't store category information if not necessary
                        actionDict.pop(u"cat", None)
                    self._setPeerActionSettings(pluginName, actionName, actionDict)
                    get_notification_center().emitPrivacySettingsChanged(pluginName, actionName)
                
    def discard(self):
        """Discards all modifications since the last save"""
        self._modifications = {}
    
    
    ######################### GETTER ########################
    
    def _getActionDict(self, pluginName, actionName, source):
        if pluginName in source:
            pluginDict = source[pluginName]
            if actionName in pluginDict:
                return pluginDict[actionName]
        return None
    
    def _getSettings(self, action, category, useModified=False):
        pluginName = action.getPluginName()
        actionName = action.getName()
        
        actionDict = None
        if useModified:
            # try to use modified action dict
            actionDict = self._getActionDict(pluginName, actionName, self._modifications)
        
        if actionDict is None:
            # use action dict from unmodified settings
            actionDict = self._getActionDict(pluginName, actionName, self._settings)
            if actionDict is None:
                # there are no settings
                return None
        
        if category is None:
            return actionDict
        else:
            if u"cat" in actionDict:
                categories = actionDict[u"cat"]
                if category in categories:
                    catDict = categories[category]
                    return catDict
        return None
    
    def _getValue(self, action, category, key, default, useModified=False):
        settings = self._getSettings(action, category, useModified)
        if settings is not None and key in settings:
            return settings[key]
        return default
    
    def getAskForConfirmation(self, action, category, useModified=False):
        """Returns True if the 'ask for confirmation' checkbox is set"""
        with self._lock:
            return self._getValue(action, category, u"ask", True, useModified)
    
    def getPolicy(self, action, category, useModified=False):
        """Get the privacy policy for a peer action.
        
        Can be POLICY_NOBODY, POLICY_NOBODY_EX, POLICY_EVERYBODY_EX,
        POLICY_EVERYBODY or POLICY_BY_CATEGORY."""
        if category is None:
            default = action.getDefaultPrivacyPolicy()
        else:
            default = action.getDefaultCategoryPrivacyPolicy()
        with self._lock:
            return self._getValue(action, category, u"pol", default, useModified)
    
    def getWhitelist(self, action, category, useModified=False):
        """Returns the whitelist dictionary.
        
        The dictionary has the form {peerID : state}, where state is
        1 for whitelisted peers and 0 for explicitly not whitelisted
        peers.
        """
        with self._lock:
            return dict(self._getValue(action, category, u"wht", {}, useModified))
        
    def getBlacklist(self, action, category, useModified=False):
        """Returns the blacklist dictionary.
        
        The dictionary has the form {peerID : state}, where state is
        1 for blacklisted peers and 0 for explicitly not blacklisted
        peers.
        """
        with self._lock:
            return dict(self._getValue(action, category, u"blk", {}, useModified))
        
    def getPeerExceptions(self, action, useModified=False):
        """Returns the peer exception dictionary.
        
        The dictionary has the form {peerID : state}, where state is
        1 for peers that should be STATE_FREE by default and 0 for peers
        that should be STATE_BLOCKED by default.
        """
        with self._lock:
            return dict(self._getValue(action, None, u"exc", {}, useModified))
        
    def getExceptions(self, action, category, policy, useModified=False):
        """Returns the exception dictionary for a given policy."""
        if policy == self.POLICY_EVERYBODY_EX:
            return self.getBlacklist(action, category, useModified)
        if policy == self.POLICY_NOBODY_EX:
            return self.getWhitelist(action, category, useModified)
        if policy == self.POLICY_PEER_EXCEPTION:
            if category is not None:
                log_warning("peer exceptions do not exist for individual categories.")
            return self.getPeerExceptions(action, useModified)
        log_error("There are no exceptions for policy", policy)
                
    def getPeerState(self, peerID, action, category):
        """Return the privacy state of a peer for a given action.
        
        Can be STATE_BLOCKED, STATE_FREE, STATE_CONFIRM and STATE_UNKNOWN.
        """
        if category is None:
            defaultPolicy = action.getDefaultPrivacyPolicy()
        else:
            defaultPolicy = action.getDefaultCategoryPrivacyPolicy()
        
        with self._lock:
            settings = self._getSettings(action, category)
            if settings is not None:
                settings = dict(settings)
            else:
                settings = {}
        
        if settings is None or u"pol" not in settings:
            policy = defaultPolicy
        else:
            policy = settings[u"pol"]
            
        if policy == self.POLICY_EVERYBODY:
            return self.STATE_FREE
        if policy == self.POLICY_NOBODY:
            return self.STATE_BLOCKED
        
        if policy == self.POLICY_EVERYBODY_EX:
            if u"blk" in settings and peerID in settings[u"blk"]:
                state = settings[u"blk"][peerID]
            else:
                state = None
            
            if state == 1:
                return self.STATE_BLOCKED
            if state == 0:
                return self.STATE_FREE
        
        if policy == self.POLICY_NOBODY_EX:
            if u"wht" in settings and peerID in settings[u"wht"]:
                state = settings[u"wht"][peerID]
            else:
                state = None
            
            if state == 1:
                return self.STATE_FREE
            if state == 0:
                return self.STATE_BLOCKED
            
        if policy in (self.POLICY_EVERYBODY_EX, self.POLICY_NOBODY_EX):
            # unknown state, special handling here: look up global exception list
            with self._lock:
                actionSettings = self._getSettings(action, None)
                if actionSettings is not None:
                    actionSettings = dict(actionSettings)
                else:
                    actionSettings = {}
            
            if u"exc" in actionSettings and peerID in actionSettings[u"exc"]:
                state = actionSettings[u"exc"]
                if state == 0:
                    return self.STATE_BLOCKED
                if state == 1:
                    return self.STATE_FREE
                
            if policy == self.POLICY_NOBODY_EX:
                # default is blocked, but confirmation might be activated
                if u"ask" in settings:
                    ask = settings[u"ask"]
                else:
                    ask = True
                
                if not ask:
                    return self.STATE_BLOCKED
                else:
                    return self.STATE_CONFIRM
            else:
                # default is free
                return self.STATE_FREE
                
        return self.STATE_UNKNOWN
    
    ###################### MODIFICATION #####################
    
    def _initModification(self, action, category, actionDict=None, actionDictSource=None):
        if actionDict is None:
            # get or create action dict
            pluginName = action.getPluginName()
            if pluginName not in actionDictSource:
                actionDictSource[pluginName] = {}
            pluginDict = actionDictSource[pluginName]
                
            actionName = action.getName()
            if actionName not in pluginDict:
                if pluginName in self._settings and actionName in self._settings[pluginName]:
                    pluginDict[actionName] = self._settings[pluginName][actionName]
                else:
                    pluginDict[actionName] = {}
            actionDict = pluginDict[actionName]
    
        if category is None:
            return actionDict
        else:
            if u"cat" not in actionDict:
                actionDict[u"cat"] = {}
            categories = actionDict[u"cat"]
            if category not in categories:
                categories[category] = {}
            return categories[category]
    
    @_setter
    def setAskForConfirmation(self, _action, _category, ask, settingsDict=None):
        settingsDict[u"ask"] = ask
    
    @_setter
    def setPolicy(self, _action, _category, policy, settingsDict=None):
        settingsDict[u"pol"] = policy
    
    @_setter
    def addException(self, _action, category, policy, peerID, checkState, settingsDict=None):
        if policy == self.POLICY_NOBODY_EX:
            key = u"wht"
        elif policy == self.POLICY_EVERYBODY_EX:
            key = u"blk"
        elif policy == self.POLICY_PEER_EXCEPTION:
            if category is not None:
                log_error("There are no peer exceptions for individual categories. Resetting to None")
                return
            key = u"exc"
            
        if key not in settingsDict:
            settingsDict[key] = {}
            
        if checkState :
            settingsDict[key][peerID] = 1
        elif checkState != -1:
            settingsDict[key][peerID] = 0
        else:
            # return to unknown state
            settingsDict[key].pop(peerID, None)
    