import threading
import socket

class DataThread(threading.Thread):
    sender = ""
    size = ""
    file_path = ''
    con = 0
    
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50001)) 
            s.settimeout(5.0)
            s.listen(1)
            self.con, addr = s.accept()
            if addr==self.sender:
                self._receiveFile()
            self.con.close()
        except:
            print "I caught something"
                
        
    def stop_server(self):
        pass