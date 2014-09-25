from lunchinator import get_settings, get_server, get_notification_center, \
        lunchinator_has_gui 
from lunchinator.log import loggingFunc
from lunchinator.plugin import iface_gui_plugin
from lunchinator.peer_actions import PeerAction
from lunchinator.utilities import getValidQtParent

class _PipeFileAction(PeerAction):
    def getName(self):
        return "Pipe Text File"
    
    def appliesToPeer(self, _peerID, _peerInfo):
        return True
    
    def performAction(self, peerID, peerInfo, parent):
        from PyQt4.QtGui import QFileDialog
        fname = QFileDialog.getOpenFileName(parent, 'Pipe file')
        
        with open(fname, 'r') as f:        
            data = f.read()
        get_server().call("HELO_PIPE "+data, peerIDs=[peerID])
    
    def getMessagePrefix(self):
        return "PIPE"
    
class pipe_out(iface_gui_plugin):
    def __init__(self):
        super(pipe_out, self).__init__()
        self._outputField = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Pipe Out"
        
    def destroy_widget(self):
        self._outputField = None
        
        iface_gui_plugin.destroy_widget(self)
        
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QTextEdit, QSizePolicy
#         from PyQt4.QtCore import QSize
        
        self._outputField = QTextEdit(parent)
        self._outputField.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        return self._outputField
    
    def get_peer_actions(self):
        self._pfAction = _PipeFileAction()
        return [self._pfAction]
    
    def process_command(self, xmsg, ip, peer_info, preprocessedData=None):
        if xmsg.getCommand()=="PIPE":
            data = xmsg.getCommandPayload()
            if lunchinator_has_gui():
                self._outputField.setText(data)
                self._outputField.setStatusTip("sent by "+peer_info[u"name"])
#                 from PyQt4.QtGui import QMessageBox
#                 QMessageBox.information(None, "Piped File from "+peer_info[u"name"], "<pre>%s</pre>"%data)
            
if __name__ == '__main__':
    sv = pipe_out()
    sv.run_in_window()