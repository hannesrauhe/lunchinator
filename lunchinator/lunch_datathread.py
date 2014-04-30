import socket,sys
from lunchinator import log_exception, log_error, convert_string

def _sendFile(con, receiver, path_or_data, tcp_port, sleep, is_data):
    for numAttempts in range(10):
        sleep(500)
        try:
            con.connect((receiver, tcp_port)) 
            break           
        except Exception as e:
            numAttempts = numAttempts + 1
            if numAttempts == 10:
                log_exception("Could not initiate connection to",receiver,"on Port",tcp_port)
                return
        
    data = None
    if is_data:
        data = path_or_data
    else:
        # no utf-8, might be binary file
        with open(path_or_data, 'rb') as sendfile:           
            data = sendfile.read()
    try:
        con.sendall(data)                      
    except socket.error as e:
        #socket error messages may contain special characters, which leads to crashes on old python versions
        log_error(u"Could not send data:", convert_string(str(e)))
        raise
    
def sendFile(receiver, path_or_data, tcp_port, sleep, is_data = False):
    #sleep(5)
    con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _sendFile(con, receiver, path_or_data, tcp_port, sleep, is_data)       
    except:
        if is_data:
            log_exception("An error occured while trying to send binary data")
        else:
            log_exception("An error occured while trying to send file",path_or_data)   
         
    if con:
        con.close()     
    
def _receiveFile(con, file_path, size):
    # no utf-8, can be binary data as well
    with open(file_path, 'wb') as writefile:
        length = size
        try:
            while length:
                rec = con.recv(min(1024, length))
                writefile.write(rec)
                length -= len(rec)
        except socket.error as e:
            #socket error messages may contain special characters, which leads to crashes on old python versions
            log_error(u"Error while receiving the data, Bytes to receive left:",length,u"Error:",convert_string(str(e)))
            raise

def receiveFile(sender, file_path, size, portOrSocket, success, error):
    s = None
    bind = True
    if type(portOrSocket) == int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        s = portOrSocket
        bind = False
    
    con = None
    try: 
        if bind:
            s.bind(("", portOrSocket)) 
            s.settimeout(30.0)
            s.listen(1)
        con, addr = s.accept()
        con.settimeout(5.0)
        if addr[0]==sender:
            _receiveFile(con, file_path, size)
        else:
            log_error("Sender is not allowed to send file:",addr[0],", expected:",sender)
        success(file_path)
    except:
        log_exception("I caught something unexpected when trying to receive file",file_path, sys.exc_info()[0])
        error()
    
    if con:    
        con.close()
    s.close()
