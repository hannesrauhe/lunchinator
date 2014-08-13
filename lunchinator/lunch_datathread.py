import socket,sys
from lunchinator import log_exception, log_error, convert_string
from cStringIO import StringIO
import contextlib
import os

MAX_CHUNKSIZE = 8 * 1024 * 1024
MIN_CHUNKSIZE = 1024

class CanceledException(Exception):
    pass

def _getChunksize(dataSize):
    return max(MIN_CHUNKSIZE, min(dataSize/100, MAX_CHUNKSIZE))

def _sendFile(con, receiver, path_or_data, tcp_port, sleep, is_data, progress_call, canceled_call):
    for numAttempts in xrange(10):
        sleep(500)
        try:
            con.connect((receiver, tcp_port))
            break           
        except Exception as e:
            numAttempts = numAttempts + 1
            if numAttempts == 10:
                log_exception("Could not initiate connection to",receiver,"on Port",tcp_port)
                return

    if is_data:
        size = len(path_or_data)
    else:
        size = os.path.getsize(path_or_data)
    
    with contextlib.closing(StringIO(path_or_data) if is_data else open(path_or_data, 'rb')) as inFile:
        try:
            chunkSize = _getChunksize(size)
            
            if progress_call is None:
                chunk = inFile.read(chunkSize)
                while len(chunk) > 0:
                    con.sendall(chunk)
                    chunk = inFile.read(chunkSize)
            else:
                maxProg = size / 1024
                sent = 0
                progress_call(0, maxProg)
                while True:
                    if canceled_call is not None and canceled_call():
                        raise CanceledException()
                    curChunk = inFile.read(chunkSize)
                    con.sendall(curChunk)
                    sent += len(curChunk)
                    if sent == size:
                        # finished
                        break
                    progress_call(sent >> 10, maxProg) 
                    
                progress_call(maxProg, maxProg)
        except socket.error as e:
            #socket error messages may contain special characters, which leads to crashes on old python versions
            log_error(u"Could not send data:", convert_string(str(e)))
            raise
    
def sendFile(receiver, path_or_data, tcp_port, sleep, is_data=False, progress_call=None, canceled_call=None):
    #sleep(5)
    con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _sendFile(con, receiver, path_or_data, tcp_port, sleep, is_data, progress_call, canceled_call)
    except CanceledException:
        raise
    except:
        if is_data:
            log_exception("An error occured while trying to send binary data")
        else:
            log_exception("An error occured while trying to send file",path_or_data)
        raise   
    finally:
        if con != None:
            con.close()     
    
def _receiveFile(con, file_path, size, progress_call, canceled_call):
    # no utf-8, can be binary data as well
    with open(file_path, 'wb') as writefile:
        if progress_call is None:
            progress_call = lambda _, __ : None
        
        received = 0
        maxProg = size / 1024
        progress_call(0, maxProg)
            
        length = size
        chunkSize = max(MIN_CHUNKSIZE, min(size/100, MAX_CHUNKSIZE))
        try:
            while received < size:
                if canceled_call is not None and canceled_call():
                    raise CanceledException()
                rec = con.recv(min(chunkSize, length))
                writefile.write(rec)
                length -= len(rec)
                
                received += len(rec)
                progress_call(received >> 10, maxProg)
            progress_call(maxProg, maxProg)
        except socket.error as e:
            #socket error messages may contain special characters, which leads to crashes on old python versions
            log_error(u"Error while receiving the data, Bytes to receive left:",length,u"Error:",convert_string(str(e)))
            raise

def receiveFile(sender, file_path, size, portOrSocket, progress_call=None, canceled_call=None):
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
        con.settimeout(30.0)
        if addr[0]==sender:
            _receiveFile(con, file_path, size, progress_call, canceled_call)
        else:
            log_error("Sender is not allowed to send file:",addr[0],", expected:",sender)
        return file_path
    except CanceledException:
        raise
    except:
        log_exception("I caught something unexpected when trying to receive file",file_path, sys.exc_info()[0])
        raise
    finally:
        if con != None:
            con.close()
        s.close()
