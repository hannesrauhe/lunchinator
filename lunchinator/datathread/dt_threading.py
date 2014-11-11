from lunchinator.datathread.base import DataSenderThreadBase,\
    DataReceiverThreadBase
from lunchinator.utilities import formatException
from lunchinator.logging_mutex import loggingMutex
from lunchinator import get_settings
from threading import Thread, Timer
from functools import partial

class DataSenderThread(Thread, DataSenderThreadBase):
    def __init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger):
        Thread.__init__(self)
        DataSenderThreadBase.__init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger)
 
    def run(self):
        try:
            self.performSend()
        except:
            self.logger.warning("Error sending file: %s", formatException())
    
class DataReceiverThread(Thread, DataReceiverThreadBase):
    _mutex = None
        
    @classmethod
    def _inactiveSocketsMutex(cls):
        if cls._mutex is None:
            cls._mutex = loggingMutex("inactive sockets mutex", False, logging=get_settings().get_verbose())
        return cls._mutex
    
    @classmethod
    def _lockInactiveSockets(cls):
        cls._inactiveSocketsMutex().acquire()
        
    @classmethod
    def _unlockInactiveSockets(cls):
        cls._inactiveSocketsMutex().release()
        
    @classmethod
    def _startSocketTimeout(cls, port):
        t = Timer(30, partial(cls._socketTimedOut, port))
        t.start()
        return t
    
    @classmethod
    def _stopSocketTimeout(cls, _port, timer):
        if timer.is_alive():
            timer.cancel()
        
    def __init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger, success_func=None, err_func=None):
        Thread.__init__(self)
        DataReceiverThreadBase.__init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger) 
        
        self._successFunc = success_func
        self._errorFunc = err_func
 
    def run(self):
        try:
            self.performReceive()
            self.logger.info("Successfully received file at %s", self._targetPath)
            if self._successFunc is not None:
                self._successFunc()
        except:
#             self.error()
            self.logger.warning("Error receiving file at %s", self._targetPath, exc_info=1)
            if self._errorFunc is not None:
                self._errorFunc()
