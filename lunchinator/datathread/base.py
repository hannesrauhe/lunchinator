from lunchinator import get_settings, convert_string
from lunchinator.log import getCoreLogger
from lunchinator.utilities import getUniquePath
from lunchinator.logging_mutex import loggingMutex

import contextlib, os, tarfile, socket, errno, time
from cStringIO import StringIO
from functools import partial

class CanceledException(Exception):
    pass

class IncompleteTransfer(Exception):
    pass

class _ProgressFile(object):
    def __init__(self, name, fo, maxSize, sizeOffset, progress, canceled):
        self.name = name
        self._fo = fo
        self._maxSize = maxSize
        self._sizeOffset = sizeOffset
        self._progress = progress
        self._canceled = canceled
        
    def read(self, size=None):
        if self._canceled():
            raise CanceledException()
        readData = self._fo.read(size)
        self._progress((self._sizeOffset + len(readData)) >> 10, self._maxSize)
        self._sizeOffset += len(readData)
        return readData

    def fileno(self):
        return self._fo.fileno()
    
    def close(self):
        self._fo.close()

class DataThreadBase(object):
    _MAX_CHUNKSIZE = 8 * 1024 * 1024
    _MIN_CHUNKSIZE = 1024

    @classmethod
    def _getChunksize(cls, dataSize):
        return max(cls._MIN_CHUNKSIZE, min(dataSize/100, cls._MAX_CHUNKSIZE))
 
    @classmethod   
    def _readSendDict(cls, sendDict, checkName=True):
        totalSize = sendDict.get(u"size", None)
        if totalSize is None:
            raise KeyError("Size not specified in send dict.")
        useTarstream = sendDict.get(u"tar", False)
        compression = sendDict.get(u"comp", "")
        name = sendDict.get(u"name", None)
        if useTarstream:
            numFiles = sendDict.get(u"count", None)
        else:
            numFiles = 1
            if checkName and name is None:
                raise KeyError("Using no tar stream and file name not specified.")
            
        return numFiles, totalSize, name, useTarstream, compression
    
    @classmethod
    def computeTotalSize(cls, filesOrData):
        """ Returns (number of files, total size) """
        if type(filesOrData) is str:
            return 1, len(filesOrData), False
        elif type(filesOrData) is list:
            size = 0
            numFiles = 0
            containsDir = False
            for path in filesOrData:
                if os.path.islink(path):
                    path = os.path.realpath(path)
                if os.path.isfile(path):
                    size += os.path.getsize(path)
                    numFiles += 1
                elif os.path.isdir(path):
                    containsDir = True
                    for dirPath, _dirNames, fileNames in os.walk(path):
                        for fileName in fileNames:
                            aPath = os.path.join(dirPath, fileName)
                            if os.path.islink(aPath):
                                numFiles += 1
                            elif os.path.isfile(aPath):
                                size += os.path.getsize(aPath)
                                numFiles += 1
            return numFiles, size, containsDir
        else:
            raise TypeError("filesOrData must be either str or list.")
        
    @classmethod
    def prepareSending(cls, filesOrData, dataName=None, compression=""):
        numFiles, totalSize, containsDir = cls.computeTotalSize(filesOrData)
        if numFiles is 0:
            raise ValueError("Trying to send no files.")
        
        if compression or containsDir or type(filesOrData) is list and len(filesOrData) > 1:
            useTarstream = True
        else:
            useTarstream = False
            
        if type(filesOrData) is str:
            name = dataName
        elif not useTarstream or numFiles is 1:
            name = os.path.basename(filesOrData[0])
        else:
            name = ""
            
        sendDict = {u"comp" : compression,
                    u"count" : numFiles,
                    u"size" : totalSize,
                    u"tar" : useTarstream,
                    u"name" : name}
        
        return sendDict
        
    def __init__(self, otherIP, portOrSocket, sendDict, logger):
        self._otherIP = otherIP
        self._portOrSocket = portOrSocket
        self._sendDict = sendDict
        self.logger = logger
        
        self.con = None
        self._userData = None
        self._canceled = False
        self._curFile = None
    
    def _progressChanged(self, curProgress, maxProgress):
        pass

    def _nextFile(self, path, fileSize):
        self._curFile = path

    def _cancel(self):
        self._canceled = True
        
    def _isCanceled(self):
        return self._canceled
        
    def setUserData(self, data):
        self._userData = data
        
    def getUserData(self):
        return self._userData
    
class DataSenderThreadBase(DataThreadBase):
    @classmethod
    def sendSingleFile(cls, receiverIP, receiverPort, filePath, logger, *args, **kwargs):
        """Send a single file to a receiver. Use receiveSingleFile() on the receiver.
        
        receiverIP -- IP address of receiver
        receiverPort -- open port on receiver address
        filePath -- path to the file to send
        """
        if type(filePath) is unicode:
            filePath = filePath.encode("utf-8")
        if type(filePath) is not str:
            raise TypeError("filePath must be a string")
        if not os.path.isfile(filePath):
            raise IOError("filePath is not a file.")
        
        sendDict = {u"size" : os.path.getsize(filePath)}
        return cls(receiverIP, receiverPort, [filePath], sendDict, logger, *args, **kwargs)
        
    @classmethod
    def sendData(cls, receiverIP, receiverPort, data, logger, *args, **kwargs):
        """Send raw data to a receiver. Use receiveSingleFile() on the receiver.
        
        receiverIP -- IP address of receiver
        receiverPort -- open port on receiver address
        data -- Raw data to send, as str
        """
        if type(data) is not str:
            raise TypeError("data must be str")
        
        sendDict = {u"size" : len(data)}
        return cls(receiverIP, receiverPort, data, sendDict, logger, *args, **kwargs)
                
    @classmethod
    def send(cls, receiverIP, receiverPort, filesOrData, sendDict, logger, *args, **kwargs):
        """Sends files or raw data to a receiver.
        
        Use this method in combination with prepareSending() to generate the
        send dict and and receive() on the receiver side.
        
        receiverIP -- IP address of receiver
        receiverPort -- open port on receiver address
        filesOrData -- either a list of file paths or a str object to be sent as raw data
        sendDict -- Dict returned by prepareSending() 
        """
        return cls(receiverIP, receiverPort, filesOrData, sendDict, logger, *args, **kwargs)
    
    def __init__(self, receiverIP, receiverPort, filesOrData, sendDict, logger):
        super(DataSenderThreadBase, self).__init__(receiverIP, receiverPort, sendDict, logger)
        
        self._filesOrData = filesOrData
        
    def _sleep(self, millis):
        time.sleep(millis / 1000.)
        
    def _iterFilesOrData(self):
        if type(self._filesOrData) is list:
            for path in self._filesOrData:
                yield path, False
        else:
            yield self._filesOrData, True
        
    def _iterSubfiles(self, val, isData):
        if isData:
            yield "", val
        
        # resolve symlinks
        if os.path.islink(val):
            val = os.path.realpath(val)
        
        if os.path.isfile(val):
            yield os.path.basename(val), val
        if os.path.isdir(val):
            baseDir = os.path.dirname(val)
            for dirPath, _dirNames, fileNames in os.walk(val):
                for fileName in fileNames:
                    path = os.path.join(dirPath, fileName)
                    yield path[len(baseDir)+1:], path
    
    def _openFileOrData(self, fileOrData, isData, name, maxProg, offset):
        inFile = StringIO(fileOrData) if isData else open(fileOrData, 'rb')
        return _ProgressFile(name, inFile, maxProg, offset, self._progressChanged, self._isCanceled)
    
    def performSend(self):
        con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            for numAttempts in xrange(10):
                self._sleep(500)
                try:
                    con.connect((self._otherIP, self._portOrSocket))
                    break
                except:
                    numAttempts = numAttempts + 1
                    if numAttempts == 10:
                        self.logger.warning("Could not initiate connection to %s on Port %s", self._otherIP, self._portOrSocket)
                        raise
        
            numFiles, totalSize, name, useTarstream, compression = self._readSendDict(self._sendDict, checkName=False)
            
            if compression and not useTarstream:
                raise ValueError("Cannot use compression without using a tar stream.")
        
            if numFiles > 1 and not useTarstream:
                raise ValueError("Cannot send multiple files without using a tar stream.")
                
            maxProg = totalSize / 1024 + 1
            self._progressChanged(0, maxProg)
            if useTarstream:
                with contextlib.closing(con.makefile("w")) as sockfile:
                    if compression is None:
                        compression = ""
                    with contextlib.closing(tarfile.open(fileobj=sockfile, mode="w|%s" % compression)) as outFile:
                        try:
                            offset = 0
                            for fileOrDirOrData, isData in self._iterFilesOrData():
                                for name, fileOrData in self._iterSubfiles(fileOrDirOrData, isData):
                                    if not isData and os.path.islink(fileOrData):
                                        # add symbolic links directly
                                        outFile.add(fileOrData, arcname=name, recursive=False)
                                    else:
                                        # use progress files for regular files.
                                        with contextlib.closing(self._openFileOrData(fileOrData, isData, name, maxProg, offset)) as inFile:
                                            if isData:
                                                tarInfo = tarfile.TarInfo()
                                                tarInfo.name = name
                                                tarInfo.size = len(fileOrData)
                                                self._nextFile(name, tarInfo.size)
                                            else:
                                                tarInfo = outFile.gettarinfo(fileobj=inFile)
                                                self._nextFile(fileOrData, tarInfo.size)
                                            outFile.addfile(tarInfo, inFile)
                                            offset += tarInfo.size
                        except socket.error:
                            # workaround to avert exception when tarfile tries to write to closed socket file
                            try:
                                outFile.fileobj.closed = True
                            except:
                                pass
                            raise
            else:
                isData = type(self._filesOrData) is str
                with contextlib.closing(StringIO(self._filesOrData) if isData else open(self._filesOrData[0], 'rb')) as inFile:
                    if isData:
                        self._nextFile(name, totalSize)
                    else:
                        self._nextFile(self._filesOrData[0], totalSize)
                    
                    chunkSize = self._getChunksize(totalSize)
                    sent = 0
                    while True:
                        if self._canceled:
                            raise CanceledException()
                        curChunk = inFile.read(chunkSize)
                        con.sendall(curChunk)
                        sent += len(curChunk)
                        if sent == totalSize:
                            # finished
                            break
                        self._progressChanged(sent >> 10, maxProg) 
                        
            self._progressChanged(maxProg, maxProg)
        finally:
            if con is not None:
                con.close()
        
class DataReceiverThreadBase(DataThreadBase):
    _inactiveSockets = {}
    _inactivePorts = []
    _timers = {}
    
    @classmethod
    def _lockInactiveSockets(cls):
        raise NotImplementedError("Implement in subclass.")
    @classmethod
    def _unlockInactiveSockets(cls):
        raise NotImplementedError("Implement in subclass.")
    @classmethod
    def _startSocketTimeout(cls, port):
        raise NotImplementedError("Implement in subclass.")
    @classmethod
    def _stopSocketTimeout(cls, port, timer):
        raise NotImplementedError("Implement in subclass.")
    
    @classmethod
    def cleanup(cls):
        cls._lockInactiveSockets()
        try:
            for port, timer in cls._timers.iteritems():
                cls._stopSocketTimeout(port, timer)
            cls._timers = {}
        finally:
            cls._unlockInactiveSockets()
    
    @classmethod
    def isPortOpen(cls, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("",port))
        except:
            return False
        finally:
            s.close()
        
        return True
 
    @classmethod
    def _socketTimedOut(cls, port):
        cls._lockInactiveSockets()
        try:
            cls._timers.pop(port, None)
            if port not in cls._inactiveSockets:
                return
            cls._inactivePorts.remove(port)
            s, _ = cls._inactiveSockets[port]
            s.close()
            del cls._inactiveSockets[port]
        except:
            getCoreLogger().exception("Socket timed out, error trying to clean up")
        finally:
            cls._unlockInactiveSockets()
 
    @classmethod
    def getOpenPort(cls, blockPort=True, category=None):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 0
        try:
            s.bind(("",0)) 
            s.settimeout(30.0)
            s.listen(1)
            port = s.getsockname()[1]
        except:
            s.close()
            raise
        finally:
            if blockPort:
                cls._lockInactiveSockets()
                try:
                    cls._inactivePorts.append(port)
                    cls._inactiveSockets[port] = (s, category)
                    
                    timer = cls._startSocketTimeout(port)
                    if port in cls._timers:
                        cls._stopSocketTimeout(port, cls._timers[port])
                    cls._timers[port] = timer
                finally:
                    cls._unlockInactiveSockets()
            else:
                s.close()
        
        return port
    
    @classmethod
    def receiveSingleFile(cls, senderIP, targetPath, fileSize, portOrSocket, logger, category=None, overwrite=False, *args, **kwargs):
        """Receives a single file.
        
        Use this function in combination with sendSingleFile() or sendData().
        
        senderIP -- IP address of sender
        targetPath -- Path of the file to be created
        fileSize -- size of the file to receive
        portOrSocket -- open port or open socket object
        overwrite -- if False, files won't be overwritten if they already exist.
                     Instead, an incrementing number is added to the file name.
        progress_call -- callback that takes (current progress, maximum progress) 
        canceled_call -- callback that takes no argument and returns True if 
                         the transfer should be canceled
        """
        sendDict = {u"size" : fileSize,
                    u"name" : os.path.basename(targetPath)}
        return cls(senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger, *args, **kwargs)
        
    @classmethod
    def receive(cls, senderIP, targetDir, portOrSocket, sendDict, logger, overwrite=False, *args, **kwargs):
        """Receives one or multiple files sent using send().
        
        senderIP-- IP address of sender
        targetDir -- Path of the file to be created if receiving a single file
                      (useTarstream == False) or the path to a directory if
                      using a tar stream.
        portOrSocket -- open port or open socket object
        sendDict -- Dict returned by prepareSending()
        overwrite -- if False, files won't be overwritten if they already exist.
                     Instead, an incrementing number is added to the file name.
        """
        numFiles, _totalSize, name, useTarstream, _compression = cls._readSendDict(sendDict)
        if useTarstream and (numFiles > 1 or not name):
            target = targetDir
        else:
            # if one file is transferred and a name is given, use it for the target path
            target = os.path.join(targetDir, name)
        
        return cls(senderIP, portOrSocket, target, overwrite, sendDict, None, logger, *args, **kwargs)
        
    def __init__(self, senderIP, portOrSocket, targetPath, overwrite, sendDict, category, logger):
        super(DataReceiverThreadBase, self).__init__(senderIP, portOrSocket, sendDict, logger)
        
        self._targetPath = os.path.abspath(convert_string(targetPath))
        self._overwrite = overwrite
        self._category = category
    
    def _writeSingleFile(self, fileSize, maxProg, offset, read, outFile):
        remaining = fileSize
        chunkSize = self._getChunksize(fileSize)
        while remaining > 0:
            if self._canceled:
                raise CanceledException()
            try:
                rec = read(min(chunkSize, remaining))
            except socket.error as e:
                if e.errno == errno.EINTR:
                    continue
                raise
            outFile.write(rec)
            remaining -= len(rec)
            offset += len(rec)
            self._progressChanged(offset >> 10, maxProg)
        return fileSize - remaining
        
    def _getFinalFilePath(self, filePath):
        if not self._overwrite:
            newPath = getUniquePath(filePath)
            if filePath == self._targetPath:
                # update target path
                self._targetPath = newPath
            filePath = newPath
        return filePath
            
    def _checkFilePath(self, tarInfo):
        filePath = os.path.abspath(os.path.join(self._targetPath, tarInfo.name))
        if not filePath.startswith(self._targetPath):
            raise ValueError("Seems there are relative paths in the tar stream: A file was going to be created at '%s'. Skipping the file." % filePath)
        return filePath
            
    def _receiveFiles(self, con, numFiles, totalSize, useTarstream, compression):
        targetIsDir = os.path.isdir(self._targetPath)
        
        if compression and not useTarstream:
            raise ValueError("Cannot use compression without using a tar stream.")
        
        maxProg = totalSize / 1024 + 1
        self._progressChanged(0, maxProg)
        
        if useTarstream:
            with contextlib.closing(con.makefile("r")) as sockfile:
                if compression is None:
                    compression = ""
                with contextlib.closing(tarfile.open(fileobj=sockfile, mode="r|%s" % compression)) as tarFile:
                    offset = 0
                    for fileIndex, tarInfo in enumerate(tarFile):
                        if fileIndex >= numFiles:
                            raise IndexError("There are more files than specified.")
                        if tarInfo.issym():
                            # extract symlink directly
                            self._checkFilePath(tarInfo)
                            tarFile.extract(tarInfo, self._targetPath)
                        else:
                            if offset + tarInfo.size > totalSize:
                                raise OverflowError("totalSize exceeded")
                            tf = tarFile.extractfile(tarInfo)
                            if tf is None:
                                # probably a directory
                                continue
                            with contextlib.closing(tf) as inFile:
                                if not targetIsDir:
                                    filePath = self._targetPath
                                else:
                                    if tarInfo.name == "":
                                        raise ValueError("targetPath is a directory, but I am receiving raw data.")
                                    filePath = self._checkFilePath(tarInfo)
                                    fileDir = os.path.dirname(filePath)
                                    if not os.path.exists(fileDir):
                                        os.makedirs(os.path.dirname(filePath))
                                    elif os.path.isfile(fileDir):
                                        raise ValueError("Cannot create file '%s', parent directory is a file." % filePath)
                                
                                filePath = self._getFinalFilePath(filePath)
                                    
                                with contextlib.closing(open(filePath, "wb")) as outFile:
                                    self._nextFile(filePath, tarInfo.size)
                                    self._writeSingleFile(tarInfo.size, maxProg, offset, lambda size : inFile.read(size), outFile)
                        
                        offset += tarInfo.size
                    if offset == totalSize and fileIndex + 1 is numFiles:
                        self._progressChanged(maxProg, maxProg)
                    else:
                        self._progressChanged(offset >> 10, maxProg)
                        raise IncompleteTransfer()
        else:
            if os.path.isdir(self._targetPath):
                raise ValueError("Target path is a directory and I don't know a file name.")
            filePath = self._getFinalFilePath(self._targetPath)
            with open(filePath, 'wb') as outFile:
                self._nextFile(filePath, totalSize)
                transferred = self._writeSingleFile(totalSize, maxProg, 0, lambda size : con.recv(size), outFile)
                if transferred == totalSize:
                    self._progressChanged(maxProg, maxProg)
                else:
                    self._progressChanged(transferred >> 10, maxProg)
                    raise IncompleteTransfer()
    
    def performReceive(self):
        # check if the port is being kept open
        port = 0
        if type(self._portOrSocket) == int:
            self._lockInactiveSockets()
            try:
                if self._portOrSocket == 0:
                    # use recently opened socket
                    for index, aPort in enumerate(self._inactivePorts):
                        aCategory = self._inactiveSockets[aPort][1]
                        if aCategory == self._category:
                            port = aPort
                            del self._inactivePorts[index]
                            self._portOrSocket = self._inactiveSockets[aPort][0]
                            del self._inactiveSockets[aPort]
                            break
                elif self._portOrSocket in self._inactiveSockets:
                    # port specifies recently opened socket
                    port = self._portOrSocket
                    port = self._portOrSocket
                    self._inactivePorts.remove(port)
                    self._portOrSocket = self._inactiveSockets[port][0]
                    del self._inactiveSockets[port]
            finally:
                self._unlockInactiveSockets()

        numFiles, totalSize, _name, useTarstream, compression = self._readSendDict(self._sendDict)
        s = None
        bind = True
        if type(self._portOrSocket) is int:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            s = self._portOrSocket
            bind = False
        
        con = None
        try: 
            if bind:
                s.bind(("", self._portOrSocket)) 
                s.settimeout(30.0)
                s.listen(1)
            retry = True
            while retry:
                try:
                    con, addr = s.accept()
                    retry = False
                except socket.error as e:
                    if e.errno == errno.EINTR:
                        retry = True
                    else:
                        raise
                except:
                    raise
            
            con.settimeout(30.0)
            if addr[0] == self._otherIP:
                self._receiveFiles(con, numFiles, totalSize, useTarstream, compression)
            else:
                self.logger.warning("Sender is not allowed to send file: %s, expected: %s", addr[0], self._otherIP)
        except IncompleteTransfer:
            raise
        except:
            if self._curFile and os.path.exists(self._curFile):
                os.remove(self._curFile)
            raise
        finally:
            if con != None:
                con.close()
            s.close()
    
