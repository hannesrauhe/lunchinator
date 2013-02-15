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
            s.close()
        except socket.error as e:
            print "Socket error:",e.strerror
        except:
            print "I caught something unexpected", sys.exc_info()[0]
 
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: 
            self._sendFile()
        except:
            print "I caught something"
                
        
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
            self.con.close()
        except socket.error as e:
            print "Socket error:",e.strerror
        except:
            print "I caught something unexpected", sys.exc_info()[0]
                
        
    def stop_server(self):
        pass