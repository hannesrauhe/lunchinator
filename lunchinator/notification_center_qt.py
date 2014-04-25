from PyQt4.QtCore import pyqtSignal, QObject

class NotificationCenterQt(QObject):
    _signalRepositoryUpdate = pyqtSignal()
    
    def registerRepositoryUpdate(self, callback):
        self._signalRepositoryUpdate.connect(callback)
    def emitRepositoryUpdate(self):
        self._signalRepositoryUpdate.emit()
