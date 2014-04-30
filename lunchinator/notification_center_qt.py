from PyQt4.QtCore import pyqtSignal, QObject
import time

class NotificationCenterQt(QObject):
    
    _signalRepositoryUpdate = pyqtSignal(set)
    def connectRepositoryUpdate(self, callback):
        self._signalRepositoryUpdate.connect(callback)
    def disconnectRepositoryUpdate(self, callback):
        self._signalRepositoryUpdate.disconnect(callback)
    def emitRepositoryUpdate(self, outdated):
        self._signalRepositoryUpdate.emit(outdated)

    _signalApplicationUpdate = pyqtSignal()
    def connectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.connect(callback)
    def disconnectApplicationUpdate(self, callback):
        self._signalApplicationUpdate.disconnect(callback)
    def emitApplicationUpdate(self):
        self._signalApplicationUpdate.emit()
        
    _signalInstallUpdate = pyqtSignal()
    def connectInstallUpdates(self, callback):
        self._signalInstallUpdate.connect(callback)
    def disconnectInstallUpdates(self, callback):
        self._signalInstallUpdate.disconnect(callback)
    def emitInstallUpdates(self):
        self._signalInstallUpdate.emit()
    
    _signalPeerAppended = pyqtSignal(unicode)
    def connectPeerAppended(self, callback):
        self._signalPeerAppended.connect(callback)
    def disconnectPeerAppended(self, callback):
        self._signalPeerAppended.disconnect(callback)
    def emitPeerAppended(self, ip):
        self._signalPeerAppended.emit(ip)
        
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
    
    _signalMessagePrepended = pyqtSignal(time.struct_time, list)
    def connectMessagePrepended(self, callback):
        self._signalMessagePrepended.connect(callback)
    def disconnectMessagePrepended(self, callback):
        self._signalMessagePrepended.disconnect(callback)
    def emitMessagePrepended(self, messageTime, senderIP, messageText):
        self._signalMessagePrepended.emit(messageTime, senderIP, messageText)
    