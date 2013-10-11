from lunchinator.lunch_datathread import sendFile, receiveFile
from PySide.QtCore import QThread, Signal, QMutex, QTimer
from lunchinator import log_info, log_exception
import socket
from functools import partial

class DataThreadBase(QThread):
    successfullyTransferred = Signal(QThread, unicode)
    errorOnTransfer = Signal(QThread)
        
    def __init__(self, parent, file_path, portOrSocket):
        super(DataThreadBase, self).__init__(parent)
        self.file_path = file_path
        self.portOrSocket = portOrSocket
        self.con = None

class DataSenderThread(DataThreadBase):
    def __init__(self, parent, receiver, pathOrData, tcp_port, isData = False):
        super(DataSenderThread, self).__init__(parent, None if isData else pathOrData, tcp_port)
        self.data = None
        if isData:
            self.data = pathOrData
        self.receiver = receiver
 
    def run(self):
        sendFile(self.receiver, self.data if self.data != None else self.file_path, self.portOrSocket, lambda msecs : QThread.msleep(msecs), self.data != None)
        
    def stop_server(self):
        pass
    
class DataReceiverThread(DataThreadBase):
    inactiveSockets = {}
    inactivePorts = []
    inactiveSocketsMutex = QMutex()
    
    def __init__(self, parent, sender, size, file_path, portOrSocket, category = None): 
        super(DataReceiverThread, self).__init__(parent, file_path, portOrSocket)
        self.sender = sender
        self.size = size
        self.category = category
        
    @classmethod
    def isPortOpen(cls, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("",port))
        except:
            return False
        finally:
            s.close()
        
        return True
 
    @classmethod
    def socketTimedOut(cls, port):
        cls.inactiveSocketsMutex.lock()
        try:
            if port not in cls.inactiveSockets:
                return
            cls.inactivePorts.remove(port)
            s, _ = cls.inactiveSockets[port]
            s.close()
            del cls.inactiveSockets[port]
        except:
            log_exception("Socket timed out, error trying to clean up")
        finally:
            cls.inactiveSocketsMutex.unlock()
 
    @classmethod
    def getOpenPort(cls, blockPort = True, category = None):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 0
        try:
            s.bind(("",0)) 
            s.settimeout(30.0)
            s.listen(1)
            port = s.getsockname()[1]
        except:
            s.close()
            raise
        finally:
            if blockPort:
                cls.inactiveSocketsMutex.lock()
                try:
                    cls.inactivePorts.append(port)
                    cls.inactiveSockets[port] = (s, category)
                    
                    QTimer.singleShot(30000, partial(cls.socketTimedOut, port))
                finally:
                    cls.inactiveSocketsMutex.unlock()
            else:
                s.close()
        
        return port
    
    def run(self):
        success = lambda finalPath : self.successfullyTransferred.emit(self, finalPath)
        error = lambda : self.errorOnTransfer.emit(self)
        port = 0
        if type(self.portOrSocket) == int:
            self.inactiveSocketsMutex.lock()
            try:
                if self.portOrSocket == 0:
                    # use recently opened socket
                    for index, aPort in enumerate(self.inactivePorts):
                        aCategory = self.inactiveSockets[aPort][1]
                        if aCategory == self.category:
                            port = aPort
                            del self.inactivePorts[index]
                            self.portOrSocket = self.inactiveSockets[aPort][0]
                            del self.inactiveSockets[aPort]
                            break
                elif self.portOrSocket in self.inactiveSockets:
                    # port specifies recently opened socket
                    port = self.portOrSocket
                    port = self.portOrSocket
                    self.inactivePorts.remove(port)
                    self.portOrSocket = self.inactiveSockets[port][0]
                    del self.inactiveSockets[port]
            finally:
                self.inactiveSocketsMutex.unlock()
        log_info("Receiving file of size %d on port %d"%(self.size,port))
        receiveFile(self.sender, self.file_path, self.size, self.portOrSocket, success, error)
        
    def stop_server(self):
        pass