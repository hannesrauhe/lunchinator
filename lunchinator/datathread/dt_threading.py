from threading import Thread
from lunchinator.datathread.base import DataSenderThreadBase,\
    DataReceiverThreadBase
from lunchinator.utilities import formatException

class DataSenderThread(Thread, DataSenderThreadBase):
    def __init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger):
        Thread.__init__(self)
        DataSenderThreadBase.__init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger)
 
    def run(self):
        try:
            self.performSend()
        except:
            self.logger.error("Error sending file: %s", formatException())
    
class DataReceiverThread(Thread, DataReceiverThreadBase):    
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
            self.logger.info("Error receiving file at %s", self._targetPath)
            if self._errorFunc is not None:
                self._errorFunc()
