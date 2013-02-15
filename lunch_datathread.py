import threading,socket,sys

class DataSenderThread(threading.Thread):
    receiver = ""
    file_path = ''
    
    def __init__(self, receiver, file_path): 
        threading.Thread.__init__(self) 
        self.receiver = receiver
        self.file_path = file_path
        
    def _sendFile(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.receiver, 50001))
            
            sendfile = open(self.file_path, 'rb')
            data = sendfile.read()
            s.sendall(data)
            data = s.recv(1)
        except socket.error as e:
            print "Socket error when trying to send file",self.file_path,e.strerror
        except:
            print "I caught something unexpected when trying to send file",self.file_path, sys.exc_info()[0]
        
        s.close()
 
    def run(self):
        self._sendFile()                
        
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
        while length:
            rec = self.con.recv(min(1024, length))
            writefile.write(rec)
            length -= len(rec)
    
        self.con.send(b'A') # single character A to prevent issues with buffering
 
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: 
            s.bind(("", 50001)) 
            s.settimeout(5.0)
            s.listen(1)
            self.con, addr = s.accept()
            if addr==self.sender:
                self._receiveFile()
        except socket.error as e:
            print "Socket error when trying to receive file",self.file_path,e.strerror
        except:
            print "I caught something unexpected when trying to receive file",self.file_path, sys.exc_info()[0]
        
        if self.con:    
            self.con.close()
        s.close()
                
        
    def stop_server(self):
        pass