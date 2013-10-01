from lunchinator.lunch_datathread import sendFile, receiveFile
from PyQt4.QtCore import QThread, pyqtSignal

class DataThreadBase(QThread):
    successfullyTransferred = pyqtSignal(QThread, str)
    errorOnTransfer = pyqtSignal(QThread, str)
        
    def __init__(self, parent, file_path, tcp_port):
        super(DataThreadBase, self).__init__(parent)
        
        self.file_path = file_path
        self.tcp_port = tcp_port
        self.con = None

class DataSenderThread(DataThreadBase):
    def __init__(self, parent, receiver, file_path, tcp_port):
        super(DataSenderThread, self).__init__(parent, file_path, tcp_port)
     
        self.receiver = receiver
 
    def run(self):
        sendFile(self.receiver, self.file_path, self.tcp_port, lambda secs : QThread.sleep(secs))
        
    def stop_server(self):
        pass
    
class DataReceiverThread(DataThreadBase):    
    def __init__(self, parent, sender, size, file_path,tcp_port): 
        super(DataReceiverThread, self).__init__(parent, file_path, tcp_port)
        
        self.sender = sender
        self.size = size
        
 
    def run(self):
        success = lambda finalPath : self.successfullyTransferred.emit(self, finalPath)
        error = lambda : self.errorOnTransfer.emit(self, None)
        receiveFile(self.sender, self.file_path, self.size, self.tcp_port, success, error)
        
    def stop_server(self):
        pass