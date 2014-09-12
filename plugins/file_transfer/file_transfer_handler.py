from PyQt4.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, QThread
from lunchinator import get_server, get_peers
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.datathread.dt_qthread import DataReceiverThread, DataSenderThread
from lunchinator.datathread.base import DataThreadBase
from lunchinator.utilities import sanitizeForFilename, getUniquePath
import os, json
from time import time

class FileTransferHandler(QObject):
    startOutgoingTransfer = pyqtSignal(int, object, object, object, int, int, bool) # transfer ID, target peer ID, filesOrData, target dir, num files, file size, is retry
    outgoingTransferStarted = pyqtSignal(int, object) # transferID, data thread
    outgoingTransferCanceled = pyqtSignal(int, bool) # transferID, is timeout
    incomingTransferStarted = pyqtSignal(object, int, object, int, int, object, object) # peer ID, transferID, target dir, num files, file size, name, data thread
    
    # private signals
    _processSendRequest = pyqtSignal(object, object, object, object)
    _processCancel = pyqtSignal(object, object)
    _processAck = pyqtSignal(object, object, object)
    _sendFilesToPeer = pyqtSignal(object, object)
    _downloadDirChanged = pyqtSignal(object)
    _overwriteChanged = pyqtSignal(bool)
    _compressionChanged = pyqtSignal(object)
    
    def __init__(self, logger, downloadDir, overwrite, compression):
        super(FileTransferHandler, self).__init__()
        
        self.logger = logger
        self._nextID = 0
        self._downloadDir = downloadDir
        self._overwrite = overwrite
        self._setCompression(compression)

        self._processSendRequest.connect(self._processSendRequestSlot)
        self._processCancel.connect(self._processCancelSlot)
        self._processAck.connect(self._processAckSlot)
        self._sendFilesToPeer.connect(self._sendFilesToPeerSlot)
        self._downloadDirChanged.connect(self._downloadDirChangedSlot)
        self._overwriteChanged.connect(self._overwriteChangedSlot)
        self._compressionChanged.connect(self._compressionChangedSlot)
        
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
    
    def _setCompression(self, comp):
        if type(comp) is unicode:
            comp = comp.encode("utf-8")
        comp = comp.lower()
        if comp == "no":
            self._compression = ""
        elif comp == "gzip":
            self._compression = "gz"
        elif comp == "bip2":
            self._compression = "bzip2"
        
    @loggingSlot()
    def _cleanup(self):
        timedOut = []
        for tID, data in self._outgoing.iteritems():
            if type(data) is tuple:
                _pID, _paths, _dict, startTime = data
                if time() - startTime > 70:
                    timedOut.append(tID)
        for tID in timedOut:
            self._outgoing.pop(tID, None)
            self.outgoingTransferCanceled.emit(tID, True)
    
    def _getNextID(self):
        nextID = self._nextID
        self._nextID += 1
        return nextID
    
    @loggingSlot(QThread, object)
    def _errorDownloading(self, thread, _message):
        self._removeDownload(thread)
            
    @loggingSlot(QThread)
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
            if (peerID, transferID) in self._incoming:
                del self._incoming[(peerID, transferID)]
                sendCancel = True
        if sendCancel:
            cancelDict = {u"id" : transferID,
                          u"up" : isUpload}
            get_server().call("HELO_FT_CANCEL %s" % json.dumps(cancelDict), peerIDs=[peerID])
    
    @pyqtSlot(QThread)
    @loggingSlot(QThread, object)
    def _removeUpload(self, thread, _msg=None):
        _, transferID = thread.getUserData()
        self._outgoing.pop(transferID, None)
        
    @pyqtSlot(QThread)
    @loggingSlot(QThread, object)
    def _removeDownload(self, thread, _path=None):
        peerID, transferID = thread.getUserData()
        self._incoming.pop((peerID, transferID), None)
        
    ############### PUBLIC INTERFACE ################
    
    # someone wants to send me a file
    def processSendRequest(self, peerID, peerIP, value, preprocessed):
        self._processSendRequest.emit(peerID, peerIP, value, preprocessed)
    @loggingSlot(object, object, object, object)
    def _processSendRequestSlot(self, peerID, peerIP, value, transferDict):
        if transferDict is None:
            try:
                transferDict = json.loads(value)
                
                if not type(transferDict) is dict:
                    self.logger.warning("transferDict is no dict.")
                    return
            except:
                self.logger.exception("Could not parse transfer dict.")
                return
        
        if not u"id" in transferDict:
            self.logger.warning("No transfer ID in transfer dict. Cannot accept request")
            return
        
        if not u"name" in transferDict:
            self.logger.warning("No file name in transfer dict. Cannot accept request")
            return
        
        if not u"size" in transferDict:
            self.logger.warning("No file size in transfer dict. Cannot accept request")
            return
        
        transferID = transferDict[u"id"]
        size = transferDict[u"size"]
        name = transferDict.get(u"name", None)
        numFiles = transferDict.get(u"count", 1)
        
        if ((peerID, transferID) in self._incoming):
            self.logger.debug(u"Ignoring duplicate file transfer from peer %s (%d)", peerID, transferID)
            return
        
        if not os.path.exists(self._downloadDir):
            os.makedirs(self._downloadDir)
        elif not os.path.isdir(self._downloadDir):
            self.logger.error("Download path %s is no directory. Cannot accept file.")
            return
        
        if numFiles > 1:
            peerName = get_peers().getDisplayedPeerName(pID=peerID)
            if peerName:
                dirName = u"%s (%s)" % (sanitizeForFilename(peerName), peerID)
            else:
                dirName = peerID
            targetDir = os.path.join(self._downloadDir, dirName)
            if not os.path.exists(targetDir) or not os.path.isdir(targetDir):
                targetDir = getUniquePath(targetDir)
                os.makedirs(targetDir)
        else:
            targetDir = self._downloadDir
        
        port = DataReceiverThread.getOpenPort(blockPort=True)
        inThread = DataReceiverThread.receive(peerIP, targetDir, port, transferDict, self.logger, overwrite=self._overwrite, parent=self)
        inThread.setUserData((peerID, transferID))
        inThread.errorOnTransfer.connect(self._errorDownloading)
        inThread.successfullyTransferred.connect(self._removeDownload)
        inThread.transferCanceled.connect(self._transferCanceled)
        inThread.finished.connect(inThread.deleteLater)
        self._incoming[(peerID, transferID)] = inThread
        inThread.start()
        
        self.incomingTransferStarted.emit(peerID, transferID, targetDir, numFiles, size, name, inThread)
        
        answerDict = {u"id" : transferID,
                      u"port" : port}
        get_server().call("HELO_FT_ACK %s" % json.dumps(answerDict), peerIPs=[peerIP])
    
    def processAck(self, peerID, peerIP, value):
        self._processAck.emit(peerID, peerIP, value)
    @loggingSlot(object, object, object)
    def _processAckSlot(self, peerID, peerIP, value):
        try:
            answerDict = json.loads(value)
            
            if not type(answerDict) is dict:
                self.logger.warning(u"answerDict is no dict.")
                return
        except:
            self.logger.exception(u"Could not parse answer dict.")
            return
        
        if not u"id" in answerDict:
            self.logger.warning(u"answerDict does not contain transfer ID.")
            return
        if not u"port" in answerDict:
            self.logger.warning(u"answerDict does not contain port.")
            return
        
        transferID = answerDict[u"id"]
        port = answerDict[u"port"]
        outData = self._outgoing.get(transferID, None)
        
        if outData is None:
            self.logger.warning(u"Received ACK for transfer that I don't know of or that already timed out.")
            return
        elif type(outData) is DataSenderThread:
            self.logger.warning(u"Received ACK for transfer that is already running.")
            return
        
        targetID, paths, sendDict, _time = outData
        if targetID != peerID:
            self.logger.warning(u"Received ACK from peer that I wasn't sending to.")
            return
        
        outThread = DataSenderThread.send(peerIP, port, paths, sendDict, self.logger, parent=self)
        outThread.transferCanceled.connect(self._transferCanceled)
        outThread.errorOnTransfer.connect(self._removeUpload)
        outThread.successfullyTransferred.connect(self._removeUpload)
        outThread.finished.connect(outThread.deleteLater)
        outThread.setUserData((peerID, transferID))
        self._outgoing[transferID] = outThread
        outThread.start()
        self.outgoingTransferStarted.emit(transferID, outThread)
    
    def processCancel(self, peerID, value):
        self._processCancel.emit(peerID, value)
    @loggingSlot(object, object)
    def _processCancelSlot(self, peerID, value):
        try:
            cancelDict = json.loads(value)
            
            if not type(cancelDict) is dict:
                self.logger.warning(u"answerDict is no dict.")
                return
        except:
            self.logger.exception("Could not parse cancel dict.")
            return
        
        if not u"id" in cancelDict:
            self.logger.warning("Cancel dict does not contain transfer ID.")
            return
        
        if not u"up" in cancelDict:
            self.logger.warning("Cancel dict does not specify whether it was an upload or not.")
            return
        
        transferID = cancelDict[u"id"]
        wasUpload = cancelDict[u"up"]
        
        if wasUpload:
            # is download on this side
            thread = self._incoming.pop((peerID, transferID), None)
            if thread is None:
                self.logger.debug("Download canceled that was not running")
                return
        else:
            thread = self._outgoing.pop(transferID, None)
            if thread is None:
                self.logger.debug("Upload canceled that was not running")
                return
            
        thread.cancelTransfer()
    
    def sendFilesToPeer(self, toSend, peerID):
        self._sendFilesToPeer.emit(toSend, peerID)
    @loggingSlot(object, object)
    def _sendFilesToPeerSlot(self, toSend, peerID, transferID=None):
        if transferID is None:
            isRetry = False
            transferID = self._getNextID()
        else:
            isRetry = True
        
        if type(toSend) in (str, unicode):
            toSend = [toSend]
        elif type(toSend) is not list:
            self.logger.error("toSend must be path of list of paths")
            return
        
        # TODO separate preparation phase
        sendDict = DataSenderThread.prepareSending(toSend, compression=self._compression)
        self._outgoing[transferID] = (peerID, toSend, sendDict, time())
        
        self.startOutgoingTransfer.emit(transferID, peerID, toSend, self._downloadDir, sendDict[u"count"], sendDict[u"size"], isRetry)
        
        sendDict[u"id"] = transferID
        get_server().call("HELO_FT %s" % json.dumps(sendDict), peerIDs=[peerID])
        
    def downloadDirChanged(self, newDir):
        self._downloadDirChanged.emit(newDir)
    @loggingSlot(object)
    def _downloadDirChangedSlot(self, newDir):
        self._downloadDir = newDir
        
    def overwriteChanged(self, overwrite):
        self._overwriteChanged.emit(overwrite)
    @loggingSlot(bool)
    def _overwriteChangedSlot(self, overwrite):
        self._overwrite = overwrite
        
    def compressionChanged(self, comp):
        self._compressionChanged.emit(comp)
    @loggingSlot(object)
    def _compressionChangedSlot(self, comp):
        self._setCompression(comp)
        
    @loggingSlot(object, object, int)
    def retrySendFileToPeer(self, toSend, peerID, oldID):
        self._sendFilesToPeerSlot(toSend, peerID, oldID)
        
    @loggingSlot(int)
    def cancelOutgoingTransfer(self, transferID):
        data = self._outgoing.get(transferID, None)
        if type(data) is tuple:
            self._outgoing.pop(transferID, None)
            self.outgoingTransferCanceled.emit(transferID, False)
        
    