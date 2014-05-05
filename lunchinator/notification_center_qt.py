from PyQt4.QtCore import pyqtSignal, QObject
import time

class NotificationCenterQt(QObject):
    
    _signalOutdatedRepositoriesChanged = pyqtSignal()
    def connectOutdatedRepositoriesChanged(self, callback):
        self._signalOutdatedRepositoriesChanged.connect(callback)
    def disconnectOutdatedRepositoriesChanged(self, callback):
        self._signalOutdatedRepositoriesChanged.disconnect(callback)
    def emitOutdatedRepositoriesChanged(self):
        self._signalOutdatedRepositoriesChanged.emit()
        
    _signalUpToDateRepositoriesChanged = pyqtSignal()
    def connectUpToDateRepositoriesChanged(self, callback):
        self._signalUpToDateRepositoriesChanged.connect(callback)
    def disconnectUpToDateRepositoriesChanged(self, callback):
        self._signalUpToDateRepositoriesChanged.disconnect(callback)
    def emitUpToDateRepositoriesChanged(self):
        self._signalUpToDateRepositoriesChanged.emit()
        
    _signalRepositoriesChanged = pyqtSignal()
    def connectRepositoriesChanged(self, callback):
        self._signalRepositoriesChanged.connect(callback)
    def disconnectRepositoriesChanged(self, callback):
        self._signalRepositoriesChanged.disconnect(callback)
    def emitRepositoriesChanged(self):
        self._signalRepositoriesChanged.emit()

    _signalApplicationUpdate = pyqtSignal()
    def connectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.connect(callback)
    def disconnectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.disconnect(callback)
    def emitApplicationUpdate(self):
        self._signalApplicationUpdate.emit()
        
    _signalUpdatesDisabled = pyqtSignal()
    def connectUpdatesDisabled(self, callback):
        self._signalUpdatesDisabled.connect(callback)
    def disconnectUpdatesDisabled(self, callback):
        self._signalUpdatesDisabled.disconnect(callback)
    def emitUpdatesDisabled(self):
        self._signalUpdatesDisabled.emit()
        
    _signalInstallUpdate = pyqtSignal()
    def connectInstallUpdates(self, callback):
        self._signalInstallUpdate.connect(callback)
    def disconnectInstallUpdates(self, callback):
        self._signalInstallUpdate.disconnect(callback)
    def emitInstallUpdates(self):
        self._signalInstallUpdate.emit()
    
    _signalRestartRequired = pyqtSignal(unicode)
    def connectRestartRequired(self, callback):
        self._signalRestartRequired.connect(callback)
    def disconnectRestartRequired(self, callback):
        self._signalRestartRequired.disconnect(callback)
    def emitRestartRequired(self, reason):
        self._signalRestartRequired.emit(reason)
    
    _signalPeerAppended = pyqtSignal(unicode, dict)
    def connectPeerAppended(self, callback):
        self._signalPeerAppended.connect(callback)
    def disconnectPeerAppended(self, callback):
        self._signalPeerAppended.disconnect(callback)
    def emitPeerAppended(self, ip, infoDict):
        self._signalPeerAppended.emit(ip, infoDict)
        
    _signalPeerUpdated = pyqtSignal(unicode, dict)
    def connectPeerUpdated(self, callback):
        self._signalPeerUpdated.connect(callback)
    def disconnectPeerUpdated(self, callback):
        self._signalPeerUpdated.disconnect(callback)
    def emitPeerUpdated(self, ip, infoDict):
        self._signalPeerUpdated.emit(ip, infoDict)
    
    _signalPeerRemoved = pyqtSignal(unicode)
    def connectPeerRemoved(self, callback):
        self._signalPeerRemoved.connect(callback)
    def disconnectPeerRemoved(self, callback):
        self._signalPeerRemoved.disconnect(callback)
    def emitPeerRemoved(self, ip):
        self._signalPeerRemoved.emit(ip)
        
    _signalMemberAppended = pyqtSignal(unicode, dict)
    def connectMemberAppended(self, callback):
        self._signalMemberAppended.connect(callback)
    def disconnectMemberAppended(self, callback):
        self._signalMemberAppended.disconnect(callback)
    def emitMemberAppended(self, ip, infoDict):
        self._signalMemberAppended.emit(ip, infoDict)
    
    _signalMemberUpdated = pyqtSignal(unicode, dict)
    def connectMemberUpdated(self, callback):
        self._signalMemberUpdated.connect(callback)
    def disconnectMemberUpdated(self, callback):
        self._signalMemberUpdated.disconnect(callback)
    def emitMemberUpdated(self, ip, infoDict):
        self._signalMemberUpdated.emit(ip, infoDict)
    
    _signalMemberRemoved = pyqtSignal(unicode)
    def connectMemberRemoved(self, callback):
        self._signalMemberRemoved.connect(callback)
    def disconnectMemberRemoved(self, callback):
        self._signalMemberRemoved.disconnect(callback)
    def emitMemberRemoved(self, ip):
        self._signalMemberRemoved.emit(ip)
    
    _signalGroupAppended = pyqtSignal(unicode, set)
    def connectGroupAppended(self, callback):
        self._signalGroupAppended.connect(callback)
    def disconnectGroupAppended(self, callback):
        self._signalGroupAppended.disconnect(callback)
    def emitGroupAppended(self, group, peer_groups):
        self._signalGroupAppended.emit(group, peer_groups)
    
    #signal with all sender info?: _signalMessagePrepended = pyqtSignal(time.struct_time, dict, list)
    _signalMessagePrepended = pyqtSignal(time.struct_time, list)
    def connectMessagePrepended(self, callback):
        self._signalMessagePrepended.connect(callback)
    def disconnectMessagePrepended(self, callback):
        self._signalMessagePrepended.disconnect(callback)
    def emitMessagePrepended(self, messageTime, senderID, messageText):
        self._signalMessagePrepended.emit(messageTime, [senderID, messageText])
    