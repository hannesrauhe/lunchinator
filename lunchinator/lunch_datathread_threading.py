from threading import Thread
from lunchinator import log_info, log_error
from lunchinator.lunch_datathread import DataSenderThreadBase,\
    DataReceiverThreadBase
from lunchinator.utilities import formatException

class DataSenderThread(Thread, DataSenderThreadBase):
    def __init__(self, receiverIP, receiverPort, filesOrData, sendDict):
        Thread.__init__(self)
        DataSenderThreadBase.__init__(self, receiverIP, receiverPort, filesOrData, sendDict)
 
    def run(self):
        try:
            self.performSend()
        except:
            log_error("Error sending file:", formatException())
    
class DataReceiverThread(Thread, DataReceiverThreadBase):    
    def __init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, success_func=None, err_func=None):
        Thread.__init__(self)
        DataReceiverThreadBase.__init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category) 
        
        self._successFunc = success_func
        self._errorFunc = err_func
 
    def run(self):
        try:
            self.performReceive()
            log_info("Successfully received file at", self._targetPath)
            if self._successFunc is not None:
                self._successFunc()
        except:
            self.error()
            log_info("Error receiving file at", self._targetPath)
            if self._errorFunc is not None:
                self._errorFunc()
