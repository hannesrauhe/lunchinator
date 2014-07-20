import json
from lunchinator import log_exception, get_settings
from lunchinator.logging_mutex import loggingMutex
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
                
    def discard(self):
        """Discards all modifications since the last save"""
        self._modifications = {}
    
    
    ######################### GETTER ########################
    
    def _getSettings(self, action, category):
        pluginName = action.getPluginName()
        if pluginName in self._settings:
            pluginDict = self._settings[pluginName]
            actionName = action.getName()
            if actionName in pluginDict:
                actionDict = pluginDict[actionName]
                if category is None:
                    return actionDict
                else:
                    if u"cat" in actionDict:
                        categories = actionDict[u"cat"]
                        if category in categories:
                            catDict = categories[category]
                            return catDict
        return None
    
    def _getValue(self, action, category, key, default):
        settings = self._getSettings(action, category)
        if settings is not None and key in settings:
            return settings[key]
        return default
    
    def getAskForConfirmation(self, action, category):
        """Returns True if the 'ask for confirmation' checkbox is set"""
        with self._lock:
            return self._getValue(action, category, u"ask", True)
    
    def getPolicy(self, action, category):
        """Get the privacy policy for a peer action.
        
        Can be POLICY_NOBODY, POLICY_NOBODY_EX, POLICY_EVERYBODY_EX,
        POLICY_EVERYBODY or POLICY_BY_CATEGORY."""
        if category is None:
            default = action.getDefaultPrivacyPolicy()
        else:
            default = action.getDefaultCategoryPrivacyPolicy()
        with self._lock:
            return self._getValue(action, category, u"pol", default)
    
    def getChecked(self, action, category):
        """Get the checked peer IDs"""
        with self._lock:
            return self._getValue(action, category, u"chk", [])
    
    def getUnchecked(self, action, category):
        """Get the explicitly unchecked peer IDs"""
        with self._lock:
            return self._getValue(action, category, u"uch", [])
        
    def getPeerState(self, peerID, action, category):
        """Return the privacy state of a peer for a given action.
        
        Can be STATE_BLOCKED, STATE_FREE, STATE_CONFIRM and STATE_UNKNOWN.
        """
        if category is None:
            defaultPolicy = action.getDefaultPrivacyPolicy()
        else:
            defaultPolicy = action.getDefaultCategoryPrivacyPolicy()
        
        with self._lock:
            settings = dict(self._getSettings(action, category))
        
        if settings is None or u"pol" not in settings:
            policy = defaultPolicy
        else:
            policy = settings[u"pol"]
            
        if policy == self.POLICY_EVERYBODY:
            return self.STATE_FREE
        if policy == self.POLICY_NOBODY:
            return self.STATE_BLOCKED
        
        if policy == self.POLICY_EVERYBODY_EX:
            if u"chk" in settings and peerID in settings[u"chk"]:
                return self.STATE_BLOCKED
            return self.STATE_FREE
        
        if policy == self.POLICY_NOBODY_EX:
            if u"chk" in settings and peerID in settings[u"chk"]:
                return self.STATE_FREE
            if u"ask" in settings:
                ask = settings[u"ask"]
            else:
                ask = True
            
            if not ask:
                return self.STATE_BLOCKED
            else:
                if u"uch" in settings and peerID in settings[u"uch"]:
                    return self.STATE_BLOCKED
                return self.STATE_CONFIRM
                
        return self.STATE_UNKNOWN
    
    ###################### MODIFICATION #####################
    
    def _initModification(self, action, category):
        pluginName = action.getPluginName()
        if pluginName not in self._modifications:
            self._modifications[pluginName] = {}
        pluginDict = self._modifications[pluginName]
            
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
    
    def setAskForConfirmation(self, action, category, ask):
        settings = self._initModification(action, category)
        settings[u"ask"] = ask
    
    def setPolicy(self, action, category, policy):
        settings = self._initModification(action, category)
        settings[u"pol"] = policy
        
    def addException(self, action, category, peerID, checked):
        settings = self._initModification(action, category)
        addKey = u"chk" if checked else u"uch" 
        rmKey = u"uch" if checked else u"chk"
        
        if addKey not in settings:
            settings[addKey] = []
        settings[addKey].append(peerID)
            
        if rmKey in settings:
            if peerID in settings[rmKey]:
                settings[rmKey].remove(peerID)
    