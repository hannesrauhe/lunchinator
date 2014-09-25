import sys, os
from lunchinator.datathread.base import DataSenderThreadBase, DataReceiverThreadBase,\
    DataThreadBase
from tempfile import NamedTemporaryFile, mkdtemp
import string
import time
from threading import Thread
from functools import partial
from cStringIO import StringIO
import contextlib
import shutil
from lunchinator import get_settings
from lunchinator.log import getCoreLogger, initializeLogger
from lunchinator.utilities import formatException

def printProgress(prog, maxProg):
    sys.stdout.write("\r%.1f" % (float(prog)/maxProg))

RECEIVER = "127.0.0.1"
SENDER = "127.0.0.1"

chars = string.ascii_letters + string.digits
tbl = string.maketrans(''.join(chr(i) for i in xrange(256)),
                       ''.join(chars[b % len(chars)] for b in range(256)))
errorSend = False
errorReceive = False

def testSend(openPort, filesOrData, sendDict):
    global errorSend
    try:
        if sendDict is not None:
            dt = DataSenderThreadBase.send(RECEIVER, openPort, filesOrData, sendDict, getCoreLogger())
        elif type(filesOrData) is str:
            dt = DataSenderThreadBase.sendData(RECEIVER, openPort, filesOrData, getCoreLogger())
        else:
            dt = DataSenderThreadBase.sendSingleFile(RECEIVER, openPort, filesOrData[0], getCoreLogger())
        dt.performSend()
    except:
        errorSend = True
        getCoreLogger().error(u"Error sending: %s", formatException())
    
def testReceive(openPort, targetPath, totalSize, sendDict):
    global errorReceive
    try:
        if sendDict is not None:
            dt = DataReceiverThreadBase.receive(SENDER, targetPath, openPort, sendDict, getCoreLogger())
        else:
            dt = DataReceiverThreadBase.receiveSingleFile(SENDER, targetPath, totalSize, openPort, getCoreLogger())
        dt.performReceive()
    except:
        errorReceive = True
        getCoreLogger().error(u"Error receiving: %s", formatException())

def makeData(size):
    global chars, tbl
    return os.urandom(size).translate(tbl)

def makeFile(path, size):
    f = NamedTemporaryFile(dir=path, delete=False)
    f.write(makeData(size))
    f.close()
    return f.name

def sendAndReceive(filesOrData, totalSize=None, targetPath=None, sendDict=None):
    global errorSend, errorReceive
    errorSend = False
    errorReceive = False
    
    openPort = DataReceiverThreadBase.getOpenPort(False)
    sendThread = Thread(target=partial(testSend, openPort, filesOrData, sendDict))
    recvThread = Thread(target=partial(testReceive, openPort, targetPath, totalSize, sendDict))
    
    startTime = time.time()
    
    recvThread.start()
    sendThread.start()
    
    recvThread.join()
    sendThread.join()
    
    endTime = time.time()
    
    if not errorSend and not errorReceive:
        getCoreLogger().info("  transfer finished, runtime: %.2fs", (endTime - startTime))
    
def compareFiles(f1, f2):
    chunk1 = f1.read(1024 * 1024)
    chunk2 = f2.read(1024 * 1024)
    while len(chunk1) > 0 and len(chunk2) > 0 and chunk1 == chunk2:
        chunk1 = f1.read(1024 * 1024)
        chunk2 = f2.read(1024 * 1024)
    if len(chunk1) or len(chunk2):
        return False
    else:
        return True
    
def iterCorrespondingFiles(path1, targetDir, useTarstream, targetName):
    if not os.path.exists(path1):
        raise ValueError("Source file %s does not exist" % path1)
    
    if os.path.islink(path1):
        path1 = os.path.realpath(path1)
    
    if os.path.isfile(path1):
        if useTarstream:
            # file names are taken from tarinfo
            yield path1, os.path.join(targetDir, os.path.basename(path1))
        else:
            # file name is taken from targetName
            yield path1, os.path.join(targetDir, targetName)
    elif os.path.isdir(path1):
        sourceDir = os.path.dirname(path1)
        for dirPath, _dirNames, fileNames in os.walk(path1):
            for fileName in fileNames:
                sourcePath = os.path.join(dirPath, fileName)
                targetPath = os.path.join(targetDir, sourcePath[len(sourceDir)+1:])
                yield sourcePath, targetPath
    
def testResult(filesOrData, targetDir, targetName, useTarstream):
    global errorSend, errorReceive
    if errorSend or errorReceive:
        return False
    
    if type(filesOrData) is str:
        with contextlib.closing(StringIO(filesOrData)) as f1:
            targetPath = os.path.join(targetDir, targetName)
            with contextlib.closing(open(targetPath, 'rb')) as f2:
                if not compareFiles(f1, f2):
                    getCoreLogger().error("ERROR: target file %s does not match source data", targetPath)
                    return False
    else:
        for path1 in filesOrData:
            for source, target in iterCorrespondingFiles(path1, targetDir, useTarstream, targetName):
                if not os.path.exists(target):
                    getCoreLogger().error("ERROR: target file %s does not exist", target)
                    return False
                if not os.path.isfile(target):
                    getCoreLogger().error("ERROR: target file %s is not a file", target)
                    return False
                with contextlib.closing(open(source, 'rb')) as f1:
                    with contextlib.closing(open(target, 'rb')) as f2:
                        if not compareFiles(f1, f2):
                            getCoreLogger().error("ERROR: target file %s does not match source file %s", target, source)
                            return False
                
    return True

def testTransfer(filesOrData, targetDir, targetName=None):
    numFiles, totalSize, containsDir = DataThreadBase.computeTotalSize(filesOrData)
    errors = False
    
    if type(filesOrData) is str or (numFiles is 1 and not containsDir):
        getCoreLogger().info("- Test single file transfer")
        sendAndReceive(filesOrData, totalSize, os.path.join(targetDir, targetName))
        if not testResult(filesOrData, targetDir, targetName, useTarstream=False):
            errors = True
    
    getCoreLogger().info("- Test uncompressed auto transfer")
    sendDict = DataThreadBase.prepareSending(filesOrData, targetName)
    sendAndReceive(filesOrData, totalSize, targetDir, sendDict)
    if not testResult(filesOrData, targetDir, targetName, useTarstream=True):
        errors = True
    
    getCoreLogger().info("- Test bzip2 compressed auto transfer")
    sendDict = DataThreadBase.prepareSending(filesOrData, targetName, "bz2")
    sendAndReceive(filesOrData, totalSize, targetDir, sendDict)
    if not testResult(filesOrData, targetDir, targetName, useTarstream=True):
        errors = True
    
    getCoreLogger().info("- Test gzip compressed auto transfer")
    sendDict = DataThreadBase.prepareSending(filesOrData, targetName, "gz")
    sendAndReceive(filesOrData, totalSize, targetDir, sendDict)
    if not testResult(filesOrData, targetDir, targetName, useTarstream=True):
        errors = True
        
    return not errors
      
if __name__ == '__main__':
    initializeLogger()
    
    get_settings().set_verbose(True)
    
    sourceDir = mkdtemp()
    targetDir = mkdtemp()
    
    FILE_SIZE = 1024 * 1024
    
    errors = False
    try:
        getCoreLogger().info("Test raw data transfer")
        inData = makeData(FILE_SIZE)
        if not testTransfer(inData, targetDir, "rawdata"):
            errors = True
         
        getCoreLogger().info("")
        getCoreLogger().info("Test file transfer (1 file)")
        inPath = makeFile(sourceDir, FILE_SIZE)
        if not testTransfer([inPath], targetDir, "rawdata.dat"):
            errors = True
         
        getCoreLogger().info("")
        getCoreLogger().info("Test file transfer (2 files)")
        inPath1 = makeFile(sourceDir, FILE_SIZE)
        inPath2 = makeFile(sourceDir, FILE_SIZE)
        if not testTransfer([inPath1, inPath2], targetDir):
            errors = True
            
        getCoreLogger().info("")
        getCoreLogger().info("Test directory transfer")
        baseDir = mkdtemp(dir=sourceDir)
        subDir = mkdtemp(dir=baseDir)
        f1 = makeFile(baseDir, 1024)
        makeFile(baseDir, 1024)
        makeFile(subDir, 1024)
        makeFile(subDir, 1024)
        sl = makeFile(subDir, 1)
        os.remove(sl)
        os.symlink(os.path.join("..", os.path.basename(f1)), sl)
        if not testTransfer([baseDir], targetDir):
            errors = True
            
        getCoreLogger().info("")
        getCoreLogger().info("Trying to send more files than announced - should fail")
        inPath1 = makeFile(sourceDir, FILE_SIZE)
        inPath2 = makeFile(sourceDir, FILE_SIZE)
        inPath3 = makeFile(sourceDir, FILE_SIZE)
        sendDict = DataThreadBase.prepareSending([inPath1, inPath2])
        sendAndReceive([inPath1, inPath2, inPath3], targetPath=targetDir, sendDict=sendDict)
        if not errorReceive:
            getCoreLogger().error("ERROR: This test should have failed.")
            errors = True
        if os.path.exists(os.path.join(targetDir, os.path.basename(inPath3))):
            getCoreLogger().error("ERROR: file %s hould not have been created", os.path.join(targetDir, os.path.basename(inPath2)))
            errors = True
            
        getCoreLogger().info("")
        getCoreLogger().info("Trying to send bigger file than announced (single file) - should fail")
        inPath1 = makeFile(sourceDir, FILE_SIZE)
        sendDict = DataThreadBase.prepareSending([inPath1])
        sendDict[u"size"] = int(0.5 * FILE_SIZE)
        sendAndReceive([inPath1], targetPath=targetDir, sendDict=sendDict)
        if not errorReceive  and not errorSend:
            getCoreLogger().error("ERROR: This test should have failed.")
            errors = True
        elif os.path.getsize(os.path.join(targetDir, os.path.basename(inPath1))) > sendDict[u"size"]:
            getCoreLogger().error("ERROR: file %s should not be bigger than %d", os.path.join(targetDir, os.path.basename(inPath1)), sendDict[u"size"])
            errors = True
          
        getCoreLogger().info("")
        getCoreLogger().info("Trying to send bigger file than announced (multiple files) - should fail")
        inPath1 = makeFile(sourceDir, FILE_SIZE)
        inPath2 = makeFile(sourceDir, FILE_SIZE)
        sendDict = DataThreadBase.prepareSending([inPath1, inPath2])
        sendDict[u"size"] = 1.5 * FILE_SIZE
        sendAndReceive([inPath1, inPath2], targetPath=targetDir, sendDict=sendDict)
        if not errorReceive:
            getCoreLogger().error("ERROR: This test should have failed.")
            errors = True
        elif os.path.exists(os.path.join(targetDir, os.path.basename(inPath2))):
            getCoreLogger().error("ERROR: file %s should not have been created", os.path.join(targetDir, os.path.basename(inPath2)))
            errors = True
        
    finally:
        getCoreLogger().info("removing tempfiles")  
        shutil.rmtree(sourceDir, ignore_errors=True)
        shutil.rmtree(targetDir, ignore_errors=True)

    if errors:
        print "There were errors. Please check."
    else:
        print "All tests succeeded."