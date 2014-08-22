from threading import Thread
from lunchinator.log import getLogger
from lunchinator.datathread.base import DataSenderThreadBase,\
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
            getLogger().error("Error sending file: %s", formatException())
    
class DataReceiverThread(Thread, DataReceiverThreadBase):    
    def __init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, success_func=None, err_func=None):
        Thread.__init__(self)
        DataReceiverThreadBase.__init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category) 
        
        self._successFunc = success_func
        self._errorFunc = err_func
 
    def run(self):
        try:
            self.performReceive()
            getLogger().info("Successfully received file at %s", self._targetPath)
            if self._successFunc is not None:
                self._successFunc()
        except:
            self.error()
            getLogger().info("Error receiving file at %s", self._targetPath)
            if self._errorFunc is not None:
                self._errorFunc()
