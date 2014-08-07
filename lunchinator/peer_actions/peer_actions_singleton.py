from lunchinator import get_settings, get_notification_center,\
    get_plugin_manager, convert_string, get_peers
from lunchinator.logging_mutex import loggingMutex
from lunchinator.peer_actions.standard_peer_actions import getStandardPeerActions
from lunchinator.privacy.privacy_settings import PrivacySettings
from lunchinator.privacy import PrivacyConfirmationDialog

class PeerActions(object):
    _instance = None
    STANDARD_PEER_ACTIONS_KEY = u"__standard__"
    
    @classmethod
    def get(cls):
        if cls._instance == None:
            cls._instance = PeerActions()
        return cls._instance
    
    def __init__(self):
        self._lock = loggingMutex("Peer Actions", logging=get_settings().get_verbose())
        self._peerActions = {} # mapping plugin name -> list of peer actions
        self._msgPrefixes = {} # mapping message prefix -> peer action
        get_notification_center().connectPluginActivated(self._pluginActivated)
        get_notification_center().connectPluginDeactivated(self._pluginDeactivated)
        
    def initialize(self):
        """Called from lunch server controller"""
        with self._lock:
            self._peerActions[self.STANDARD_PEER_ACTIONS_KEY] = getStandardPeerActions()
            self._addMessagePrefixes(self._peerActions[self.STANDARD_PEER_ACTIONS_KEY])
            
            for pi in get_plugin_manager().getAllPlugins():
                if pi.plugin_object.is_activated:
                    self._addActionsForPlugin(pi)
        
    def _addMessagePrefixes(self, actions):
        for action in actions:
            if action.getMessagePrefix():
                self._msgPrefixes[action.getMessagePrefix()] = action
        
    def _addActionsForPlugin(self, pi):
        peerActions = pi.plugin_object.get_peer_actions()
        if peerActions:
            for peerAction in peerActions:
                peerAction.setParentPlugin(pi.name, pi.plugin_object)
            self._peerActions[pi.name] = peerActions
            self._addMessagePrefixes(peerActions)
            return {pi.name : peerActions}
        return None
        
    def _removeActionsForPlugin(self, pi):
        if pi.name in self._peerActions:
            removed = {pi.name : [peerAction.getName() for peerAction in self._peerActions[pi.name]]}
            del self._peerActions[pi.name]
            return removed
        return None
        
    def _pluginActivated(self, pluginName, category):
        pluginName = convert_string(pluginName)
        category = convert_string(category)
        pi = get_plugin_manager().getPluginByName(pluginName, category)
        if pi:
            with self._lock:
                added = self._addActionsForPlugin(pi)
            if added:
                get_notification_center().emitPeerActionsAdded(added)
                
    def _pluginDeactivated(self, pluginName, category):
        pluginName = convert_string(pluginName)
        category = convert_string(category)
        pi = get_plugin_manager().getPluginByName(pluginName, category)
        if pi:
            with self._lock:
                removed = self._removeActionsForPlugin(pi)
            if removed:
                get_notification_center().emitPeerActionsRemoved(removed)
            
    def _getPeerActions(self, peerID=None, peerInfo=None, ignoreApplies=False, filterFunc=None):
        result = {}
        with self._lock:
            for pluginName, actions in self._peerActions.iteritems():
                newActions = []
                for action in actions:
                    if ignoreApplies:
                        applies = True
                    elif peerInfo is not None or not action.peerMustBeOnline():
                        applies = action.appliesToPeer(peerID, peerInfo)
                    else:
                        applies = False
                    if applies:
                        if filterFunc == None or filterFunc(pluginName, action):
                            newActions.append(action)
                if newActions:
                    result[pluginName] = newActions
                    
        return result
            
    def getPeerActions(self, peerID, peerInfo, filterFunc=None):
        """Returns a dictionary of peer actions for the given peer.
        
        The dictionary contains plugin names as keys and a list of the
        plugin's peer actions as values.
        
        filterFunc - Function that takes (plugin name, peer action) and
        returns True if the action should be added to the result. 
        """
        return self._getPeerActions(peerID, peerInfo, filterFunc=filterFunc)
    
    def getAllPeerActions(self):
        """Returns a dictionary of all peer actions.
        
        The dictionary contains plugin names as keys and a list of the
        plugin's peer actions as values.
        """
        return self._getPeerActions(ignoreApplies=True)
        
    def getPeerAction(self, msgPrefix):
        with self._lock:
            if msgPrefix in self._msgPrefixes:
                return self._msgPrefixes[msgPrefix]
        
    def shouldProcessMessage(self, action, category, peerID, mainGUI):
        if category is None:
            category = PrivacySettings.NO_CATEGORY
        
        state = action.getPeerState(peerID, category)
        if state == PrivacySettings.STATE_FREE:
            return True
        if state == PrivacySettings.STATE_BLOCKED:
            return False
        if state == PrivacySettings.STATE_CONFIRM:
            if mainGUI is None:
                # no gui -> no confirmation
                return False
            peerName = get_peers().getDisplayedPeerName(peerID)
            
            if action.usesPrivacyCategories():
                if category == PrivacySettings.NO_CATEGORY:
                    message = "%s wants to perform the following action: %s (uncategorized)" % (peerName, action.getName())
                else:
                    message = "%s wants to perform the following action: %s, in category %s" % (peerName, action.getName(), category)
            else:
                message = "%s wants to perform the following action: %s" % (peerName, action.getName())
            dialog = PrivacyConfirmationDialog(mainGUI,
                                               "Confirmation",
                                               message,
                                               peerName,
                                               peerID,
                                               action,
                                               category)
            dialog.exec_()
            return dialog.result() == PrivacyConfirmationDialog.Accepted
        return False
        