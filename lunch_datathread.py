import threading,socket,sys,time

class DataSenderThread(threading.Thread):
    receiver = ""
    file_path = ''
    con = None
    
    def __init__(self, receiver, file_path): 
        threading.Thread.__init__(self) 
        self.receiver = receiver
        self.file_path = file_path
        
    def _sendFile(self):
        try:
            self.con.connect((self.receiver, 50001))            
        except socket.error as e:
            print "Could not initiate connection to",self.receiver,e.strerror
            raise
        
        sendfile = open(self.file_path, 'rb')           
        data = sendfile.read()
        
        try:
            self.con.sendall(data)                      
        except socket.error as e:
            print "Could not send data",e.strerror
            raise
        
 
    def run(self):
        time.sleep(5)
        self.con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sendFile()       
        except:
            print "An error occured while trying to send file",self.file_path, sys.exc_info()[0]   
             
        if self.con:
            self.con.close()     
        
    def stop_server(self):
        pass
    
class DataReceiverThread(threading.Thread):
    sender = ""
    size = ""
    file_path = ''
    con = None
    
    def __init__(self, sender, size, file_path): 
        threading.Thread.__init__(self) 
        self.sender = sender
        self.size = size
        self.file_path = file_path
        
    def _receiveFile(self):
        writefile = open(self.file_path, 'wb')
        length = self.size
        try:
            while length:
                rec = self.con.recv(min(1024, length))
                writefile.write(rec)
                length -= len(rec)
        except socket.error as e:
            print "Error while receiving the data, Bytes to receive left:",length,"Error:",e.strerror
            raise
 
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: 
            s.bind(("", 50001)) 
            s.settimeout(5.0)
            s.listen(1)
            self.con, addr = s.accept()
            if addr==self.sender:
                self._receiveFile()
        except:
            print "I caught something unexpected when trying to receive file",self.file_path, sys.exc_info()[0]
        
        if self.con:    
            self.con.close()
        s.close()
                
        
    def stop_server(self):
        pass