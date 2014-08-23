from lunchinator.datathread.base import DataSenderThreadBase, DataReceiverThreadBase, CanceledException,\
    IncompleteTransfer
from PyQt4.QtCore import QThread, pyqtSignal
from lunchinator.utilities import formatException
import socket
from lunchinator.log.logging_slot import loggingSlot

class DataSenderThread(QThread, DataSenderThreadBase):
    successfullyTransferred = pyqtSignal(QThread) # self
    errorOnTransfer = pyqtSignal(QThread, object) # self, error message
    progressChanged = pyqtSignal(int, int) # progress, max progress
    transferCanceled = pyqtSignal(QThread)
    nextFile = pyqtSignal(object, int) # name/path, size
    
    def __init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger, parent):
        QThread.__init__(self, parent)
        DataSenderThreadBase.__init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger)
 
    def _progressChanged(self, newVal, maxVal):
        self.progressChanged.emit(newVal, maxVal)
    
    def _nextFile(self, path, fileSize):
        super(DataSenderThread, self)._nextFile(path, fileSize)
        self.nextFile.emit(path, fileSize)
    
    @loggingSlot()
    def cancelTransfer(self):
        self._cancel()
        
    def run(self):
        try:
            self.performSend()
            self.successfullyTransferred.emit(self)
        except CanceledException:
            self.transferCanceled.emit(self)
        except socket.error:
            msg = formatException()
            self.logger.error("Error sending: %s", msg)
            self.errorOnTransfer.emit(self, msg)
        except:
            self.logger.exception("Error sending")
            self.errorOnTransfer.emit(self, formatException())
        
class DataReceiverThread(QThread, DataReceiverThreadBase):
    successfullyTransferred = pyqtSignal(QThread, object) # self, target path
    errorOnTransfer = pyqtSignal(QThread, object) # self, error message
    progressChanged = pyqtSignal(int, int) # progress, max progress
    transferCanceled = pyqtSignal(QThread)
    nextFile = pyqtSignal(object, int) # name/path, size
    
    @classmethod
    def _useQMutex(cls):
        return True
    
    def __init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger, parent):
        QThread.__init__(self, parent)
        DataReceiverThreadBase.__init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger)
    
    @loggingSlot()
    def cancelTransfer(self):
        self._cancel()
        
    def _progressChanged(self, curProgress, maxProgress):
        self.progressChanged.emit(curProgress, maxProgress)
        
    def _nextFile(self, path, fileSize):
        super(DataReceiverThread, self)._nextFile(path, fileSize)
        self.nextFile.emit(path, fileSize)
        
    def run(self):
        try:
            self.performReceive()
            self.successfullyTransferred.emit(self, self._targetPath)
        except CanceledException:
            self.transferCanceled.emit(self)
        except IncompleteTransfer:
            self.errorOnTransfer.emit(self, u"Transfer incomplete.")
        except:
            self.logger.exception("Error receiving")
            self.errorOnTransfer.emit(self, formatException())
