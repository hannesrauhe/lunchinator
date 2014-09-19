from lunchinator import get_settings, get_server, get_notification_center, \
        lunchinator_has_gui 
from lunchinator.log import loggingFunc
from lunchinator.plugin import iface_gui_plugin
from lunchinator.peer_actions import PeerAction
from lunchinator.utilities import getValidQtParent
import sys
from datetime import datetime, timedelta

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
    
class messages_table(iface_gui_plugin):
    def __init__(self):
        super(messages_table, self).__init__()
        self.messagesTable = None
        self._dailyTrigger = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Group Messages"
    
    def sendMessageClicked(self, text):
        if get_server().controller != None:
            get_server().controller.sendMessageClicked(None, text)
        
    def destroy_widget(self):
        if self._dailyTrigger != None:
            self._dailyTrigger.timeout.disconnect(self._updateTimes)
            self._dailyTrigger.stop()
            self._dailyTrigger.deleteLater()
                    
        get_notification_center().disconnectMessagePrepended(self.messagesModel.messagePrepended)
        get_notification_center().disconnectDisplayedPeerNameChanged(self.messagesModel.updateSenders)
        
        self.messagesModel = None
        self.messagesTable = None
        
        iface_gui_plugin.destroy_widget(self)
        
    def _displayedPeerNameChanged(self, _pid, _newName, _infoDict):
        self.messagesModel.updateSenders()
        
    def _updateDailyTrigger(self):
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delta = midnight - now
        self._dailyTrigger.start((delta.seconds + 1) * 1000 + delta.microseconds / 1000)
        
    @loggingFunc
    def _updateTimes(self):
        self.logger.debug("It's a new day, update the message times.")
        self.messagesModel.updateTimes()
        self._updateDailyTrigger()
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import Qt, QTimer
        from lunchinator.table_widget import TableWidget
        from messages_table.messages_table_model import MessagesTableModel
        
        self.messagesTable = TableWidget(parent, "Send Message", self.sendMessageClicked, placeholderText="Enter a message", sortingEnabled=False)
        
        # initialize messages table
        self.messagesModel = MessagesTableModel(parent)
        self.messagesTable.setModel(self.messagesModel)
        self.messagesTable.setColumnWidth(0, 120)
        self.messagesTable.setColumnWidth(1, 90)
        
        get_notification_center().connectMessagePrepended(self.messagesModel.messagePrepended)
        get_notification_center().connectDisplayedPeerNameChanged(self.messagesModel.updateSenders)
        
        self._dailyTrigger = QTimer(parent)
        self._dailyTrigger.timeout.connect(self._updateTimes)
        self._dailyTrigger.setSingleShot(True)
        self._updateDailyTrigger()
        
        return self.messagesTable
    
    def add_menu(self,menu):
        pass
    
    def get_peer_actions(self):
        self._pfAction = _PipeFileAction()
        return [self._pfAction]
    
    def process_command(self, xmsg, ip, peer_info, preprocessedData=None):
        if xmsg.getCommand()=="PIPE":
            data = xmsg.getCommandPayload()
            if lunchinator_has_gui():
                from PyQt4.QtGui import QMessageBox
                QMessageBox.information(None, "Piped File from "+peer_info[u"name"], "<pre>%s</pre>"%data)
            else:
                print data
                print "by "+peer_info[u"name"]
            