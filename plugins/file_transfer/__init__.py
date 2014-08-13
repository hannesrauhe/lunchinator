from lunchinator.plugin import iface_gui_plugin
from lunchinator.utilities import canUseBackgroundQThreads, getValidQtParent
from lunchinator.peer_actions import PeerAction
import os
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
        
        self._gui = FileTransferWidget(parent, self)
        
        if canUseBackgroundQThreads():
            from PyQt4.QtCore import QThread
            self._handlerThread = QThread()
        else:
            self._handlerThread = None
            
        self._handler = FileTransferHandler(self._gui, self.get_option(u"download_dir"))
        if self._handlerThread is not None:
            self._handlerThread.moveToThread(self._handlerThread)
            self._handlerThread.start()
            
        self._gui.retry.connect(self._handler.retrySendFileToPeer)
        self._handler.startOutgoingTransfer.connect(self._gui.startOutgoingTransfer)
        self._handler.outgoingTransferStarted.connect(self._gui.outgoingTransferStarted)
        self._handler.outgoingTransferTimedOut.connect(self._gui.outgoingTransferTimedOut)
        self._handler.incomingTransferStarted.connect(self._gui.incomingTransferStarted)
            
        return self._gui
    
    def destroy_widget(self):
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
        
    def process_event(self, cmd, value, peerIP, peerInfo):
        if not cmd.startswith(u"HELO_FT"):
            return
        
        peerID = peerInfo[u"ID"]
        
        subcmd = cmd[7:]
        if subcmd == u"":
            self._handler.processSendRequest(peerID, peerIP, value)
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
