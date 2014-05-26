def _connectFunc(func):
    signal = func.__name__[7:]
    def newFunc(self, callback):
        func(self, callback)
        self._addCallback(signal, callback)
    return newFunc
        
def _disconnectFunc(func):
    signal = func.__name__[10:]
    def newFunc(self, callback):
        func(self, callback)
        self._removeCallback(signal, callback)
    return newFunc

def _emitFunc(func):
    signal = func.__name__[4:]
    def newFunc(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self._emit(signal, *args, **kwargs)
    return newFunc

class NotificationCenter(object):
    """Central class for notification passing within Lunchinator."""
    _instance = None
    
    @classmethod
    def getSingletonInstance(cls):
        """Returns the singleton NotificationCenter instance.
        
        Don't call this method directly. Use
        lunchinator.get_notification_center() instead.
        """
        if cls._instance == None:
            # fallback if it was not set from outside
            cls._instance = NotificationCenter()
        return cls._instance
    
    @classmethod
    def setSingletonInstance(cls, instance):
        """Set the singleton instance.
        
        This is being taken care of in the lunch server controller.
        """
        cls._instance = instance
        
    def __init__(self):
        self._callbacks = {}
        
    def _addCallback(self, signal, callback):
        if signal in self._callbacks:
            callbacks = self._callbacks[signal]
        else:
            callbacks = []
        callbacks.append(callback)
        self._callbacks[signal] = callbacks
        
    def _removeCallback(self, signal, callback):
        if not signal in self._callbacks:
            return
        callbacks = self._callbacks[signal]
        callbacks.remove(callback)
    
    def _emit(self, signal, *args, **kwargs):
        if not signal in self._callbacks:
            return
        for callback in self._callbacks[signal]:
            callback(*args, **kwargs)

    """Called whenever the set of outdated plugin repository changes."""    
    @_connectFunc
    def connectOutdatedRepositoriesChanged(self, callback):
        pass
    @_disconnectFunc
    def disconnectOutdatedRepositoriesChanged(self, callback):
        pass
    @_emitFunc
    def emitOutdatedRepositoriesChanged(self):
        pass
    
    """Called whenever the set of up-to-date plugin repositories changes."""
    @_connectFunc
    def connectUpToDateRepositoriesChanged(self, callback):
        pass
    @_disconnectFunc
    def disconnectUpToDateRepositoriesChanged(self, callback):
        pass
    @_emitFunc
    def emitUpToDateRepositoriesChanged(self):
        pass
    
    """Called whenever the list of plugin repositories is changed."""
    @_connectFunc
    def connectRepositoriesChanged(self, callback):
        pass
    @_disconnectFunc
    def disconnectRepositoriesChanged(self, callback):
        pass
    @_emitFunc
    def emitRepositoriesChanged(self):
        pass
    
    """Called when an update for Lunchinator is detected."""
    @_connectFunc
    def connectApplicationUpdate(self, callback):
        pass
    @_disconnectFunc
    def disconnectApplicationUpdate(self, callback):
        pass
    @_emitFunc
    def emitApplicationUpdate(self):
        pass
    
    """Called when updates are disabled (online_update is deactivated)"""
    @_connectFunc
    def connectUpdatesDisabled(self, callback):
        pass
    @_disconnectFunc
    def disconnectUpdatesDisabled(self, callback):
        pass
    @_emitFunc
    def emitUpdatesDisabled(self):
        pass
    
    """Notifies online_update that it should install the updates.
    Shouldn't be connected anywhere else, since the application terminates
    during the update."""
    @_connectFunc
    def connectInstallUpdates(self, callback):
        pass
    @_disconnectFunc
    def disconnectInstallUpdates(self, callback):
        pass
    @_emitFunc
    def emitInstallUpdates(self):
        pass
    
    """Emitted when an action was performed that requires a restart,
    e.g., the plugin repositories were changed. GUI controller will
    display a restart action in the Lunchinator menu."""
    @_connectFunc
    def connectRestartRequired(self, callback):
        pass
    @_disconnectFunc
    def disconnectRestartRequired(self, callback):
        pass
    @_emitFunc
    def emitRestartRequired(self, reason):
        pass
    
    @_connectFunc
    def connectPeerAppended(self, callback):
        pass
    @_disconnectFunc
    def disconnectPeerAppended(self, callback):
        pass
    @_emitFunc
    def emitPeerAppended(self, peerID, infoDict):
        pass
        
    @_connectFunc
    def connectPeerUpdated(self, callback):
        pass
    @_disconnectFunc
    def disconnectPeerUpdated(self, callback):
        pass
    @_emitFunc
    def emitPeerUpdated(self, peerID, infoDict):
        pass
    
    @_connectFunc
    def connectPeerRemoved(self, callback):
        pass
    @_disconnectFunc
    def disconnectPeerRemoved(self, callback):
        pass
    @_emitFunc
    def emitPeerRemoved(self, peerID):
        pass    
    
    @_connectFunc
    def connectMemberAppended(self, callback):
        pass
    @_disconnectFunc
    def disconnectMemberAppended(self, callback):
        pass
    @_emitFunc
    def emitMemberAppended(self, peerID, infoDict):
        pass
    
    @_connectFunc
    def connectMemberUpdated(self, callback):
        pass
    @_disconnectFunc
    def disconnectMemberUpdated(self, callback):
        pass
    @_emitFunc
    def emitMemberUpdated(self, peerID, infoDict):
        pass
    
    @_connectFunc
    def connectMemberRemoved(self, callback):
        pass
    @_disconnectFunc
    def disconnectMemberRemoved(self, callback):
        pass
    @_emitFunc
    def emitMemberRemoved(self, peerID):
        pass    
        
    @_connectFunc
    def connectGroupAppended(self, callback):
        pass
    @_disconnectFunc
    def disconnectGroupAppended(self, callback):
        pass
    @_emitFunc
    def emitGroupAppended(self, group, peer_groups):
        pass
    
    @_connectFunc
    def connectGroupChanged(self, callback):
        pass
    @_disconnectFunc
    def disconnectGroupChanged(self, callback):
        pass
    @_emitFunc
    def emitGroupChanged(self, oldGroup, newGroup):
        pass
    
    @_connectFunc
    def connectMessagePrepended(self, callback):
        pass
    @_disconnectFunc
    def disconnectMessagePrepended(self, callback):
        pass
    @_emitFunc
    def emitMessagePrepended(self, messageTime, senderID, messageText):
        pass
    
    @_connectFunc
    def connectGeneralSettingChanged(self, callback):
        pass
    @_disconnectFunc
    def disconnectGeneralSettingChanged(self, callback):
        pass
    @_emitFunc
    def emitGeneralSettingChanged(self, settingName):
        pass
    
if __name__ == '__main__':
    def _testCallback(a, b, c):
        print a, b, c
    
    print "foo"
    nc = NotificationCenter()
    nc.connectMessagePrepended(_testCallback)
    nc.emitMessagePrepended("a", "b", [{"foo":4}])