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
    
    ########## DON'T OVERRIDE ##########    
    def getPluginName(self):
        """Returns the parent plugin's name."""
        return None
    
    def getPluginObject(self):
        """Returns the parent plugin's plugin object"""
        return self._pluginObject
    
    def setParentPlugin(self, pluginName, pluginObject):
        self._pluginName = pluginName
        self._pluginObject = pluginObject
        