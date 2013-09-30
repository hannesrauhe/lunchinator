import socket,sys
from lunchinator import log_exception
from PyQt4.QtCore import QThread, pyqtSignal

class DataThreadBase(QThread):
    successfullyTransferred = pyqtSignal(QThread, str)
    errorOnTransfer = pyqtSignal(QThread)
        
    def __init__(self, parent, file_path, tcp_port):
        super(DataThreadBase, self).__init__(parent)
        
        self.file_path = file_path
        self.tcp_port = tcp_port
        self.con = None

class DataSenderThread(DataThreadBase):
    def __init__(self, parent, receiver, file_path, tcp_port):
        super(DataSenderThread, self).__init__(parent, file_path, tcp_port)
     
        self.receiver = receiver
        
    def _sendFile(self):
        try:
            self.con.connect((self.receiver, self.tcp_port))            
        except socket.error as e:
            log_exception("Could not initiate connection to",self.receiver,"on Port",self.tcp_port,e.strerror)
            raise
        
        sendfile = open(self.file_path, 'rb')           
        data = sendfile.read()
        
        try:
            self.con.sendall(data)                      
        except socket.error as e:
            log_exception("Could not send data",e.strerror)
            raise
        
 
    def run(self):
        QThread.sleep(5)
        self.con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sendFile()       
        except:
            log_exception("An error occured while trying to send file",self.file_path, sys.exc_info()[0])   
             
        if self.con:
            self.con.close()     
        
    def stop_server(self):
        pass
    
class DataReceiverThread(DataThreadBase):    
    def __init__(self, parent, sender, size, file_path,tcp_port): 
        super(DataReceiverThread, self).__init__(parent, file_path, tcp_port)
        
        self.sender = sender
        self.size = size
        
    def _receiveFile(self):
        writefile = open(self.file_path, 'wb')
        length = self.size
        try:
            while length:
                rec = self.con.recv(min(1024, length))
                writefile.write(rec)
                length -= len(rec)
        except socket.error as e:
            log_exception("Error while receiving the data, Bytes to receive left:",length,"Error:",e.strerror)
            raise
 
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: 
            s.bind(("", self.tcp_port)) 
            s.settimeout(30.0)
            s.listen(1)
            self.con, addr = s.accept()
            self.con.settimeout(5.0)
            if addr[0]==self.sender:
                self._receiveFile()
            else:
                raise Exception("Sender is not allowed to send file:",addr[0],", expected:",self.sender)
            self.successfullyTransferred.emit(self, self.file_path)
        except:
            log_exception("I caught something unexpected when trying to receive file",self.file_path, sys.exc_info()[0])
            self.errorOnTransfer.emit(self)
        
        if self.con:    
            self.con.close()
        s.close()
        
    def stop_server(self):
        pass