from lunchinator import get_settings, get_notification_center,\
    get_plugin_manager, convert_string
from lunchinator.logging_mutex import loggingMutex

class PeerActions(object):
    _instance = None
    
    @classmethod
    def get(cls):
        if cls._instance == None:
            cls._instance = PeerActions()
        return cls._instance
    
    def __init__(self):
        self._lock = loggingMutex("Peer Actions", logging=get_settings().get_verbose())
        self._peerActions = {} # mapping plugin name -> list of peer actions
        get_notification_center().connectPluginActivated(self._pluginActivated)
        get_notification_center().connectPluginDeactivated(self._pluginDeactivated)
        
    def initialize(self):
        """Called from lunch server controller"""
        with self._lock:
            for pi in get_plugin_manager().getAllPlugins():
                if pi.plugin_object.is_activated:
                    self._addActionsForPlugin(pi)
                        
        get_notification_center().emitPeerActionsChanged()
        
    def _addActionsForPlugin(self, pi):
        peerActions = pi.plugin_object.get_peer_actions()
        if peerActions:
            for peerAction in peerActions:
                peerAction.setParentPlugin(pi.name, pi.plugin_object)
            self._peerActions[pi.name] = peerActions
            return True
        return False
        
    def _removeActionsForPlugin(self, pi):
        if pi.name in self._peerActions:
            del self._peerActions[pi.name]
            return True
        return False
        
    def _pluginActivated(self, pluginName, category):
        pluginName = convert_string(pluginName)
        category = convert_string(category)
        pi = get_plugin_manager().getPluginByName(pluginName, category)
        if pi:
            with self._lock:
                added = self._addActionsForPlugin(pi)
            if added:
                get_notification_center().emitPeerActionsChanged()
                
    def _pluginDeactivated(self, pluginName, category):
        pluginName = convert_string(pluginName)
        category = convert_string(category)
        pi = get_plugin_manager().getPluginByName(pluginName, category)
        if pi:
            with self._lock:
                removed = self._removeActionsForPlugin(pi)
            if removed:
                get_notification_center().emitPeerActionsChanged()
        
    def iterPeerActions(self, peerID, peerInfo):
        """Iterates over peer actions for the given peer
        
        Yields tuples (parent plugin's name, peer action)
        """
        with self._lock:
            for pluginName, actions in self._peerActions:
                for action in actions:
                    if action.appliesToPeer(peerID, peerInfo):
                        yield (pluginName, action)
            
    def _getPeerActions(self, peerID=None, peerInfo=None, ignoreApplies=False, filterFunc=None):
        result = {}
        with self._lock:
            for pluginName, actions in self._peerActions.iteritems():
                newActions = []
                for action in actions:
                    if ignoreApplies or action.appliesToPeer(peerID, peerInfo):
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
