from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
import os
from lunchinator import get_server, log_exception, log_error, log_warning,\
    log_debug
import json
from lunchinator.lunch_datathread_qt import DataReceiverThread, DataSenderThread,\
    DataThreadBase
import itertools
from time import time

class FileTransferHandler(QObject):
    startOutgoingTransfer = pyqtSignal(int, object, object, bool) # transfer ID, target peer ID, path, is retry
    outgoingTransferStarted = pyqtSignal(int, object) # transferID, data thread
    outgoingTransferTimedOut = pyqtSignal(int) # transferID
    incomingTransferStarted = pyqtSignal(object, int, object, object) # peer ID, transferID, name, data thread
    
    # private signals
    _processSendRequest = pyqtSignal(object, object, object, object)
    _processCancel = pyqtSignal(object, object)
    _processAck = pyqtSignal(object, object, object)
    _sendFileToPeer = pyqtSignal(object, object)
    _downloadDirChanged = pyqtSignal(object)
    
    def __init__(self, gui, downloadDir):
        super(FileTransferHandler, self).__init__()
        
        self._gui = gui
        self._nextID = 0
        self._downloadDir = downloadDir

        self._processSendRequest.connect(self._processSendRequestSlot)
        self._processCancel.connect(self._processCancelSlot)
        self._processAck.connect(self._processAckSlot)
        self._sendFileToPeer.connect(self._sendFileToPeerSlot)
        self._downloadDirChanged.connect(self._downloadDirChangedSlot)
        
        self._incoming = {} # (peer ID, transfer ID) -> DataReceiverThread
        self._outgoing = {} # transfer ID -> (target ID, file path, start time) or DataSenderThread
        
        self._cleanupTimer = QTimer(self)
        self._cleanupTimer.timeout.connect(self._cleanup)
        self._cleanupTimer.start(10000)
        
    def deactivate(self):
        for aDict in (self._incoming, self._outgoing):
            for data in aDict.values():
                if isinstance(data, DataThreadBase):
                    data.cancelTransfer()
                    data.wait()
            
        if self._cleanupTimer is not None and self._cleanupTimer.isActive():
            self._cleanupTimer.stop()
            self._cleanupTimer.deleteLater()
            self._cleanupTimer = None
    
    @pyqtSlot()
    def _cleanup(self):
        timedOut = []
        for tID, data in self._outgoing.iteritems():
            if type(data) is tuple:
                _pID, _path, startTime = data
                if time() - startTime > 70:
                    timedOut.append(tID)
        for tID in timedOut:
            self._outgoing.pop(tID, None)
            self.outgoingTransferTimedOut.emit(tID)
    
    def _getNextID(self):
        nextID = self._nextID
        self._nextID += 1
        return nextID
    
    def _getReceivedFilePath(self, name):
        defaultPath = os.path.join(self._downloadDir, name)
        if not os.path.exists(defaultPath):
            return defaultPath
        
        # have to make it unique
        name, ext = os.path.splitext(defaultPath)
        for i in itertools.count(2):
            newPath = "%s %d%s" % (name, i, ext)
            if not os.path.exists(newPath):
                return newPath
    
    @pyqtSlot(object, object)
    def _errorDownloading(self, thread, _message):
        if os.path.exists(thread.getPath()):
            os.remove(thread.getPath())
        self._removeDownload(thread)
            
    @pyqtSlot(object)
    def _transferCanceled(self, thread):
        peerID, transferID = thread.getUserData()
        sendCancel = False
        isUpload = False
        if type(thread) is DataSenderThread:
            if transferID in self._outgoing:
                del self._outgoing[transferID]
                sendCancel = True
                isUpload = True
        else:
            if os.path.exists(thread.getPath()):
                os.remove(thread.getPath())
            if (peerID, transferID) in self._incoming:
                del self._incoming[(peerID, transferID)]
                sendCancel = True
        if sendCancel:
            cancelDict = {u"id" : transferID,
                          u"up" : isUpload}
            get_server().call("HELO_FT_CANCEL %s" % json.dumps(cancelDict), peerIDs=[peerID])
    
    @pyqtSlot(object)
    @pyqtSlot(object, object)
    def _removeUpload(self, thread, _msg=None):
        _, transferID = thread.getUserData()
        self._outgoing.pop(transferID, None)
        
    @pyqtSlot(object)
    def _removeDownload(self, thread):
        peerID, transferID = thread.getUserData()
        self._incoming.pop((peerID, transferID), None)
        
    ############### PUBLIC INTERFACE ################
    
    # someone wants to send me a file
    def processSendRequest(self, peerID, peerIP, value, preprocessed):
        self._processSendRequest.emit(peerID, peerIP, value, preprocessed)
    @pyqtSlot(object, object, object, object)
    def _processSendRequestSlot(self, peerID, peerIP, value, transferDict):
        if transferDict is None:
            try:
                transferDict = json.loads(value)
                
                if not type(transferDict) is dict:
                    log_error("transferDict is no dict.")
                    return
            except:
                log_exception("Could not parse transfer dict.")
                return
        
        if not u"id" in transferDict:
            log_error("No transfer ID in transfer dict. Cannot accept request")
            return
        
        if not u"name" in transferDict:
            log_error("No file name in transfer dict. Cannot accept request")
            return
        
        if not u"size" in transferDict:
            log_error("No file size in transfer dict. Cannot accept request")
            return
        
        transferID = transferDict[u"id"]
        name = transferDict[u"name"]
        size = transferDict[u"size"]
        
        filePath = self._getReceivedFilePath(name)
        # create file s.t. an icon can be determined
        open(filePath, 'wb').close()
        
        port = DataReceiverThread.getOpenPort(blockPort=True)
        inThread = DataReceiverThread(self,
                                      peerIP,
                                      size,
                                      filePath,
                                      port)
        inThread.setUserData((peerID, transferID))
        inThread.errorOnTransfer.connect(self._errorDownloading)
        inThread.successfullyTransferred.connect(self._removeDownload)
        inThread.transferCanceled.connect(self._transferCanceled)
        inThread.finished.connect(inThread.deleteLater)
        self._incoming[(peerID, transferID)] = inThread
        inThread.start()
        
        self.incomingTransferStarted.emit(peerID, transferID, filePath, inThread)
        
        answerDict = {u"id" : transferID,
                      u"port" : port}
        get_server().call("HELO_FT_ACK %s" % json.dumps(answerDict), peerIPs=[peerIP])
    
    def processAck(self, peerID, peerIP, value):
        self._processAck.emit(peerID, peerIP, value)
    @pyqtSlot(object, object, object)
    def _processAckSlot(self, peerID, peerIP, value):
        try:
            answerDict = json.loads(value)
            
            if not type(answerDict) is dict:
                log_error(u"answerDict is no dict.")
                return
        except:
            log_exception(u"Could not parse answer dict.")
            return
        
        if not u"id" in answerDict:
            log_error(u"answerDict does not contain transfer ID.")
            return
        if not u"port" in answerDict:
            log_error(u"answerDict does not contain port.")
            return
        
        transferID = answerDict[u"id"]
        port = answerDict[u"port"]
        outData = self._outgoing.get(transferID, None)
        
        if outData is None:
            log_warning(u"Received ACK for transfer that I don't know of or that already timed out.")
            return
        elif type(outData) is DataSenderThread:
            log_warning(u"Received ACK for transfer that is already running.")
            return
        
        targetID, filePath, _time = outData
        if targetID != peerID:
            log_warning(u"Received ACK from peer that I wasn't sending to.")
            return
        
        outThread = DataSenderThread(self, peerIP, filePath, port, isData=False)
        outThread.transferCanceled.connect(self._transferCanceled)
        outThread.errorOnTransfer.connect(self._removeUpload)
        outThread.successfullyTransferred.connect(self._removeUpload)
        outThread.finished.connect(outThread.deleteLater)
        outThread.setUserData((peerID, transferID))
        self._outgoing[transferID] = outThread
        self.outgoingTransferStarted.emit(transferID, outThread)
        outThread.start()
    
    def processCancel(self, peerID, value):
        self._processCancel.emit(peerID, value)
    @pyqtSlot(object, object)
    def _processCancelSlot(self, peerID, value):
        try:
            cancelDict = json.loads(value)
            
            if not type(cancelDict) is dict:
                log_error(u"answerDict is no dict.")
                return
        except:
            log_exception("Could not parse cancel dict.")
            return
        
        if not u"id" in cancelDict:
            log_error("Cancel dict does not contain transfer ID.")
            return
        
        if not u"up" in cancelDict:
            log_error("Cancel dict does not specify whether it was an upload or not.")
            return
        
        transferID = cancelDict[u"id"]
        wasUpload = cancelDict[u"up"]
        
        if wasUpload:
            # is download on this side
            thread = self._incoming.pop((peerID, transferID), None)
            if thread is None:
                log_debug("Download canceled that was not running")
                return
        else:
            thread = self._outgoing.pop(transferID, None)
            if thread is None:
                log_debug("Upload canceled that was not running")
                return
            
        thread.cancelTransfer()
    
    def sendFileToPeer(self, path, peerID):
        self._sendFileToPeer.emit(path, peerID)
    @pyqtSlot(object, object)
    def _sendFileToPeerSlot(self, path, peerID, transferID=None):
        if transferID is None:
            isRetry = False
            transferID = self._getNextID()
        else:
            isRetry = True
        
        self._outgoing[transferID] = (peerID, path, time())
        
        self.startOutgoingTransfer.emit(transferID, peerID, path, isRetry)
        
        transferDict = {u"id" : transferID,
                        u"name" : os.path.basename(path),
                        u"size" : os.path.getsize(path)}
        get_server().call("HELO_FT %s" % json.dumps(transferDict), peerIDs=[peerID])
        
    def downloadDirChanged(self, newDir):
        self._downloadDirChanged.emit(newDir)
    @pyqtSlot(object)
    def _downloadDirChangedSlot(self, newDir):
        self._downloadDir = newDir
        
    @pyqtSlot(object, object, int)
    def retrySendFileToPeer(self, path, peerID, oldID):
        self._sendFileToPeerSlot(path, peerID, oldID)