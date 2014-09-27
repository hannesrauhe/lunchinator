from lunchinator.datathread.base import DataSenderThreadBase, DataReceiverThreadBase, CanceledException,\
    IncompleteTransfer
from lunchinator import get_settings
from lunchinator.utilities import formatException
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.logging_mutex import loggingMutex
from PyQt4.QtCore import QThread, QTimer, pyqtSignal
import socket
from functools import partial

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
            self.logger.warning("Error sending: %s", msg)
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
    
    _mutex = None
    
    @classmethod
    def _inactiveSocketsMutex(cls):
        if cls._mutex is None:
            cls._mutex = loggingMutex("inactive sockets mutex", True, logging=get_settings().get_verbose())
        return cls._mutex
    
    @classmethod
    def _lockInactiveSockets(cls):
        cls._inactiveSocketsMutex().lock()
        
    @classmethod
    def _unlockInactiveSockets(cls):
        cls._inactiveSocketsMutex().unlock()
        
    @classmethod
    def _startSocketTimeout(cls, port):
        t = QTimer()
        t.setSingleShot(True)
        t.timeout.connect(partial(cls._socketTimedOut, port))
        t.start(30000)
        return t
    
    @classmethod
    def _stopSocketTimeout(cls, _port, timer):
        if timer.isActive():
            timer.stop()
    
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
        except socket.timeout:
            self.errorOnTransfer.emit(self, u"Socket timed out.")
        except:
            self.logger.exception("Error receiving")
            self.errorOnTransfer.emit(self, formatException())
