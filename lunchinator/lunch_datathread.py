import socket,sys
from lunchinator import log_exception
import codecs

def _sendFile(con, receiver, file_path, tcp_port):
    try:
        con.connect((receiver, tcp_port))            
    except socket.error as e:
        log_exception("Could not initiate connection to",receiver,"on Port",tcp_port,e.strerror)
        raise
    
    with codecs.open(file_path, 'rb', 'utf-8') as sendfile:           
        data = sendfile.read()
        try:
            con.sendall(data)                      
        except socket.error as e:
            log_exception("Could not send data",e.strerror)
            raise
    
def sendFile(receiver, file_path, tcp_port, sleep):
    sleep(5)
    con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _sendFile(con, receiver, file_path, tcp_port)       
    except:
        log_exception("An error occured while trying to send file",file_path, sys.exc_info()[0])   
         
    if con:
        con.close()     
    
def _receiveFile(con, file_path, size):
    with codecs.open(file_path, 'wb', 'utf-8') as writefile:
        length = size
        try:
            while length:
                rec = con.recv(min(1024, length))
                writefile.write(rec)
                length -= len(rec)
        except socket.error as e:
            log_exception("Error while receiving the data, Bytes to receive left:",length,"Error:",e.strerror)
            raise

def receiveFile(sender, file_path, size, tcp_port, success, error):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: 
        s.bind(("", tcp_port)) 
        s.settimeout(30.0)
        s.listen(1)
        con, addr = s.accept()
        con.settimeout(5.0)
        if addr[0]==sender:
            _receiveFile(con, file_path, size)
        else:
            raise Exception("Sender is not allowed to send file:",addr[0],", expected:",sender)
        success(file_path)
    except:
        log_exception("I caught something unexpected when trying to receive file",file_path, sys.exc_info()[0])
        error()
    
    if con:    
        con.close()
    s.close()
