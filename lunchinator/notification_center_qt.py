from PyQt4.QtCore import pyqtSignal, QObject, Qt, QCoreApplication
import time

class NotificationCenterQt(QObject):
    def processSignalsNow(self):
        QCoreApplication.processEvents()
        
    def finish(self):
        pass
    
    _signalPluginActivated = pyqtSignal(unicode, unicode)
    def connectPluginActivated(self, callback):
        self._signalPluginActivated.connect(callback, type=Qt.QueuedConnection)
    def disconnectPluginActivated(self, callback):
        self._signalPluginActivated.disconnect(callback)
    def emitPluginActivated(self, pluginName, category):
        self._signalPluginActivated.emit(pluginName, category)
        
    _signalPluginWillBeDeactivated = pyqtSignal(unicode, unicode)
    def connectPluginWillBeDeactivated(self, callback):
        # need direct connection here to ensure steps can be done before the plugin is actually deactivated.
        self._signalPluginWillBeDeactivated.connect(callback, type=Qt.DirectConnection)
    def disconnectPluginWillBeDeactivated(self, callback):
        self._signalPluginWillBeDeactivated.disconnect(callback)
    def emitPluginWillBeDeactivated(self, pluginName, category):
        self._signalPluginWillBeDeactivated.emit(pluginName, category)
        
    _signalPluginDeactivated = pyqtSignal(unicode, unicode)
    def connectPluginDeactivated(self, callback):
        self._signalPluginDeactivated.connect(callback, type=Qt.QueuedConnection)
    def disconnectPluginDeactivated(self, callback):
        self._signalPluginDeactivated.disconnect(callback)
    def emitPluginDeactivated(self, pluginName, category):
        self._signalPluginDeactivated.emit(pluginName, category)
        
    _signalOutdatedRepositoriesChanged = pyqtSignal()
    def connectOutdatedRepositoriesChanged(self, callback):
        self._signalOutdatedRepositoriesChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectOutdatedRepositoriesChanged(self, callback):
        self._signalOutdatedRepositoriesChanged.disconnect(callback)
    def emitOutdatedRepositoriesChanged(self):
        self._signalOutdatedRepositoriesChanged.emit()
        
    _signalUpToDateRepositoriesChanged = pyqtSignal()
    def connectUpToDateRepositoriesChanged(self, callback):
        self._signalUpToDateRepositoriesChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectUpToDateRepositoriesChanged(self, callback):
        self._signalUpToDateRepositoriesChanged.disconnect(callback)
    def emitUpToDateRepositoriesChanged(self):
        self._signalUpToDateRepositoriesChanged.emit()
        
    _signalRepositoriesChanged = pyqtSignal()
    def connectRepositoriesChanged(self, callback):
        self._signalRepositoriesChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectRepositoriesChanged(self, callback):
        self._signalRepositoriesChanged.disconnect(callback)
    def emitRepositoriesChanged(self):
        self._signalRepositoriesChanged.emit()

    _signalApplicationUpdate = pyqtSignal()
    def connectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.connect(callback, type=Qt.QueuedConnection)
    def disconnectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.disconnect(callback)
    def emitApplicationUpdate(self):
        self._signalApplicationUpdate.emit()
        
    _signalUpdatesDisabled = pyqtSignal()
    def connectUpdatesDisabled(self, callback):
        self._signalUpdatesDisabled.connect(callback, type=Qt.QueuedConnection)
    def disconnectUpdatesDisabled(self, callback):
        self._signalUpdatesDisabled.disconnect(callback)
    def emitUpdatesDisabled(self):
        self._signalUpdatesDisabled.emit()
        
    _signalInstallUpdate = pyqtSignal()
    def connectInstallUpdates(self, callback):
        self._signalInstallUpdate.connect(callback, type=Qt.QueuedConnection)
    def disconnectInstallUpdates(self, callback):
        self._signalInstallUpdate.disconnect(callback)
    def emitInstallUpdates(self):
        self._signalInstallUpdate.emit()
    
    _signalRestartRequired = pyqtSignal(unicode)
    def connectRestartRequired(self, callback):
        self._signalRestartRequired.connect(callback, type=Qt.QueuedConnection)
    def disconnectRestartRequired(self, callback):
        self._signalRestartRequired.disconnect(callback)
    def emitRestartRequired(self, reason):
        self._signalRestartRequired.emit(reason)
    
    _signalPeerAppended = pyqtSignal(unicode, object)
    def connectPeerAppended(self, callback):
        self._signalPeerAppended.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerAppended(self, callback):
        self._signalPeerAppended.disconnect(callback)
    def emitPeerAppended(self, peerID, infoDict):
        self._signalPeerAppended.emit(peerID, infoDict)
        
    _signalPeerUpdated = pyqtSignal(unicode, object)
    def connectPeerUpdated(self, callback):
        self._signalPeerUpdated.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerUpdated(self, callback):
        self._signalPeerUpdated.disconnect(callback)
    def emitPeerUpdated(self, peerID, infoDict):
        self._signalPeerUpdated.emit(peerID, infoDict)
    
    _signalPeerRemoved = pyqtSignal(unicode)
    def connectPeerRemoved(self, callback):
        self._signalPeerRemoved.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerRemoved(self, callback):
        self._signalPeerRemoved.disconnect(callback)
    def emitPeerRemoved(self, peerID):
        self._signalPeerRemoved.emit(peerID)
        
    _signalDisplayedPeerNameChanged = pyqtSignal(unicode, unicode, object)
    def connectDisplayedPeerNameChanged(self, callback):
        self._signalDisplayedPeerNameChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectDisplayedPeerNameChanged(self, callback):
        self._signalDisplayedPeerNameChanged.disconnect(callback)
    def emitDisplayedPeerNameChanged(self, peerID, newDisplayedName, infoDict):
        self._signalDisplayedPeerNameChanged.emit(peerID, newDisplayedName, infoDict)
        
    _signalPeerNameAdded = pyqtSignal(unicode, unicode)
    def connectPeerNameAdded(self, callback):
        self._signalPeerNameAdded.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerNameAdded(self, callback):
        self._signalPeerNameAdded.disconnect(callback)
    def emitPeerNameAdded(self, peerID, peerName):
        self._signalPeerNameAdded.emit(peerID, peerName)
        
    _signalAvatarChanged = pyqtSignal(unicode, unicode)
    def connectAvatarChanged(self, callback):
        self._signalAvatarChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectAvatarChanged(self, callback):
        self._signalAvatarChanged.disconnect(callback)
    def emitAvatarChanged(self, peerID, newFileName):
        self._signalAvatarChanged.emit(peerID, newFileName)
        
    _signalMemberAppended = pyqtSignal(unicode, object)
    def connectMemberAppended(self, callback):
        self._signalMemberAppended.connect(callback, type=Qt.QueuedConnection)
    def disconnectMemberAppended(self, callback):
        self._signalMemberAppended.disconnect(callback)
    def emitMemberAppended(self, peerID, infoDict):
        self._signalMemberAppended.emit(peerID, infoDict)
    
    _signalMemberUpdated = pyqtSignal(unicode, object)
    def connectMemberUpdated(self, callback):
        self._signalMemberUpdated.connect(callback, type=Qt.QueuedConnection)
    def disconnectMemberUpdated(self, callback):
        self._signalMemberUpdated.disconnect(callback)
    def emitMemberUpdated(self, peerID, infoDict):
        self._signalMemberUpdated.emit(peerID, infoDict)
    
    _signalMemberRemoved = pyqtSignal(unicode)
    def connectMemberRemoved(self, callback):
        self._signalMemberRemoved.connect(callback, type=Qt.QueuedConnection)
    def disconnectMemberRemoved(self, callback):
        self._signalMemberRemoved.disconnect(callback)
    def emitMemberRemoved(self, peerID):
        self._signalMemberRemoved.emit(peerID)
    
    _signalGroupAppended = pyqtSignal(unicode, set)
    def connectGroupAppended(self, callback):
        self._signalGroupAppended.connect(callback, type=Qt.QueuedConnection)
    def disconnectGroupAppended(self, callback):
        self._signalGroupAppended.disconnect(callback)
    def emitGroupAppended(self, group, peer_groups):
        self._signalGroupAppended.emit(group, peer_groups)
        
    _signalGroupChanged = pyqtSignal(unicode, unicode)
    def connectGroupChanged(self, callback):
        self._signalGroupChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectGroupChanged(self, callback):
        self._signalGroupChanged.disconnect(callback)
    def emitGroupChanged(self, oldGroup, newGroup):
        self._signalGroupChanged.emit(oldGroup, newGroup)
    
    # signal with all sender info?: _signalMessagePrepended = pyqtSignal(time.struct_time, dict, list)
    _signalMessagePrepended = pyqtSignal(time.struct_time, unicode, unicode)
    def connectMessagePrepended(self, callback):
        self._signalMessagePrepended.connect(callback, type=Qt.QueuedConnection)
    def disconnectMessagePrepended(self, callback):
        self._signalMessagePrepended.disconnect(callback)
    def emitMessagePrepended(self, messageTime, senderID, messageText):
        self._signalMessagePrepended.emit(messageTime, senderID, messageText)
    
    _signalGeneralSettingChanged = pyqtSignal(unicode)
    def connectGeneralSettingChanged(self, callback):
        self._signalGeneralSettingChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectGeneralSettingChanged(self, callback):
        self._signalGeneralSettingChanged.disconnect(callback)
    def emitGeneralSettingChanged(self, settingName):
        self._signalGeneralSettingChanged.emit(settingName)
        
    _signalDBSettingChanged = pyqtSignal(unicode)
    def connectDBSettingChanged(self, callback):
        self._signalDBSettingChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectDBSettingChanged(self, callback):
        self._signalDBSettingChanged.disconnect(callback)
    def emitDBSettingChanged(self, dbConnName):
        self._signalDBSettingChanged.emit(dbConnName)
        
    _signalPeerActionsAdded = pyqtSignal(object) # dict of {added plugin's name, [action]}
    def connectPeerActionsAdded(self, callback):
        self._signalPeerActionsAdded.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerActionsAdded(self, callback):
        self._signalPeerActionsAdded.disconnect(callback)
    def emitPeerActionsAdded(self, added):
        self._signalPeerActionsAdded.emit(added)
        
    _signalPeerActionsRemoved = pyqtSignal(object) # dict of {removed plugin's name : [action name]}
    def connectPeerActionsRemoved(self, callback):
        self._signalPeerActionsRemoved.connect(callback, type=Qt.QueuedConnection)
    def disconnectPeerActionsRemoved(self, callback):
        self._signalPeerActionsRemoved.disconnect(callback)
    def emitPeerActionsRemoved(self, removed):
        self._signalPeerActionsRemoved.emit(removed)
        
    _signalPrivacySettingsChanged = pyqtSignal(unicode, unicode)
    def connectPrivacySettingsChanged(self, callback):
        self._signalPrivacySettingsChanged.connect(callback, type=Qt.QueuedConnection)
    def disconnectPrivacySettingsChanged(self, callback):
        self._signalPrivacySettingsChanged.disconnect(callback)
    def emitPrivacySettingsChanged(self, pluginName, actionName):
        self._signalPrivacySettingsChanged.emit(pluginName, actionName)
        
    _signalPrivacySettingsDiscarded = pyqtSignal(unicode, unicode)
    def connectPrivacySettingsDiscarded(self, callback):
        self._signalPrivacySettingsDiscarded.connect(callback, type=Qt.QueuedConnection)
    def disconnectPrivacySettingsDiscarded(self, callback):
        self._signalPrivacySettingsDiscarded.disconnect(callback)
    def emitPrivacySettingsDiscarded(self, pluginName, actionName):
        self._signalPrivacySettingsDiscarded.emit(pluginName, actionName)
        