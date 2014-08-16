from lunchinator.plugin import iface_gui_plugin
from lunchinator.utilities import canUseBackgroundQThreads, getValidQtParent,\
    formatSize
from lunchinator.peer_actions import PeerAction
import os, json
from PyQt4.Qt import QFileDialog
from lunchinator import convert_string

class _TransferFileAction(PeerAction):
    def getName(self):
        return u"Send File"
    
    def appliesToPeer(self, _peerID, peerInfo):
        return u"FT_v" in peerInfo
    
    def performAction(self, peerID, _peerInfo, parentWidget):
        self.getPluginObject().sendFileToPeer(peerID, parentWidget)
        
    def getMessagePrefix(self):
        return "FT"
    
    def preProcessMessageData(self, msgData):
        try:
            transferDict = json.loads(msgData)
            
            if not type(transferDict) is dict:
                raise TypeError("transferDict is no dict.")
            return transferDict
        except:
            raise ValueError("Could not parse transfer dict.")
    
    def getConfirmationMessage(self, _peerID, peerName, msgData):
        size = msgData.get(u"size", -1)
        name = msgData.get(u"name", u"<unknown name>")
        
        return u"%s wants to send you the file \"%s\" (%s)." % (peerName, name, formatSize(size))

class file_transfer(iface_gui_plugin):
    VERSION_INITIAL = 0
    VERSION_CURRENT = VERSION_INITIAL
    
    def __init__(self):
        super(file_transfer, self).__init__()
        self.options = [((u"download_dir", u"Save received files in directory", self._downloadDirChanged), os.path.expanduser("~"))]
    
    def get_displayed_name(self):
        return u"File Transfer"
        
    def activate(self):
        iface_gui_plugin.activate(self)
        self._sendFileAction = _TransferFileAction()
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from file_transfer.file_transfer_widget import FileTransferWidget
        from file_transfer.file_transfer_handler import FileTransferHandler
        
        
        if canUseBackgroundQThreads():
            from PyQt4.QtCore import QThread
            self._handlerThread = QThread()
        else:
            self._handlerThread = None
            
        self._handler = FileTransferHandler(self.get_option(u"download_dir"))
        if self._handlerThread is not None:
            self._handlerThread.moveToThread(self._handlerThread)
            self._handlerThread.start()
        
        self._gui = FileTransferWidget(parent, self)
        self._toolWindow = FileTransferWidget(parent, self, asWindow=True)
        self._toolWindow.setWindowTitle("File Transfers")

        for gui in (self._gui, self._toolWindow):        
            gui.retry.connect(self._handler.retrySendFileToPeer)
            gui.cancel.connect(self._handler.cancelOutgoingTransfer)
            self._handler.startOutgoingTransfer.connect(gui.startOutgoingTransfer)
            self._handler.outgoingTransferStarted.connect(gui.outgoingTransferStarted)
            self._handler.outgoingTransferCanceled.connect(gui.outgoingTransferCanceled)
            self._handler.incomingTransferStarted.connect(gui.incomingTransferStarted)
        
        return self._gui
    
    def destroy_widget(self):
        for gui in (self._gui, self._toolWindow):        
            gui.retry.disconnect(self._handler.retrySendFileToPeer)
            gui.cancel.disconnect(self._handler.cancelOutgoingTransfer)
            self._handler.startOutgoingTransfer.disconnect(gui.startOutgoingTransfer)
            self._handler.outgoingTransferStarted.disconnect(gui.outgoingTransferStarted)
            self._handler.outgoingTransferCanceled.disconnect(gui.outgoingTransferCanceled)
            self._handler.incomingTransferStarted.disconnect(gui.incomingTransferStarted)
        
        self._handler.deactivate()
        if self._handlerThread is not None:
            self._handlerThread.quit()
            self._handlerThread.wait()
            self._handlerThread.deleteLater()
            self._handlerThread = None
        self._handler = None
        
        iface_gui_plugin.destroy_widget(self)
    
    def extendsInfoDict(self):
        return True
        
    def extendInfoDict(self, infoDict):
        infoDict[u"FT_v"] = self.VERSION_CURRENT
        
    def get_peer_actions(self):
        return [self._sendFileAction]
        
    def process_event(self, cmd, value, peerIP, peerInfo, preprocessedData=None):
        if not cmd.startswith(u"HELO_FT"):
            return
        
        peerID = peerInfo[u"ID"]
        
        subcmd = cmd[7:]
        if subcmd == u"":
            self._handler.processSendRequest(peerID, peerIP, value, preprocessedData)
        elif subcmd == u"_ACK":
            self._handler.processAck(peerID, peerIP, value)
        elif subcmd == u"_CANCEL":
            self._handler.processCancel(peerID, value)
            
    def getSendFileAction(self):
        return self._sendFileAction
            
    def sendFileToPeer(self, peerID, parent):
        selectedFile = QFileDialog.getOpenFileName(parent, caption="Choose a file to upload")
        selectedFile = convert_string(selectedFile)
        if selectedFile:
            self._handler.sendFileToPeer(selectedFile, peerID)
        
    def _downloadDirChanged(self, _setting, newVal):
        self._handler.downloadDirChanged(newVal)
        return newVal

if __name__ == '__main__':
    ft = file_transfer()
    ft.hasConfigOption = lambda _ : False
    ft.run_in_window()
