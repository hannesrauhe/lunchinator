from lunchinator.lunch_datathread import sendFile, receiveFile
import time
from threading import Thread
from lunchinator import log_info

class DataThreadBase(Thread):
    def __init__(self, file_path, tcp_port):
        super(DataThreadBase, self).__init__()
        
        self.file_path = file_path
        self.tcp_port = tcp_port
        self.con = None

class DataSenderThread(DataThreadBase):
    def __init__(self, receiver, path_or_data, tcp_port, is_data = False):
        super(DataSenderThread, self).__init__(None if is_data else path_or_data, tcp_port)
        
        self.data = None
        if is_data:
            self.data = path_or_data
        self.receiver = receiver
 
    def run(self):
        sendFile(self.receiver, self.data if self.data != None else self.file_path, self.tcp_port, lambda secs : time.sleep(secs * 0.001), self.data != None)
        
    def stop_server(self):
        pass
    
class DataReceiverThread(DataThreadBase):    
    def __init__(self, sender, size, file_path,tcp_port): 
        super(DataReceiverThread, self).__init__(file_path, tcp_port)
        
        self.sender = sender
        self.size = size
        
    def success(self, filePath):
        log_info("successfully received file %s" % filePath)
    
    def error(self):
        log_info("Error receiving file")
 
    def run(self):
        receiveFile(self.sender, self.file_path, self.size, self.tcp_port, self.success, self.error)
        
    def stop_server(self):
        pass