# @author: Cornelius Ratsch, Hannes Rauhe
# @summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, \
                        QLineEdit, QMenu, QInputDialog
from PyQt4.QtCore import QTimer, Qt, pyqtSlot
from lunchinator import get_server, get_peers, get_notification_center
from lunchinator.log import getLogger
from lunchinator.lunch_button import LunchButton
from lunchinator.log.logging_slot import loggingSlot
from time import time, strftime, struct_time
            
class SimpleViewWidget(QWidget):   
    # http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
    colors = ["C44D58", "C7F464", "4ECDC4", "556270", "FF6B6B"]
    
    def __init__(self, parent):
        super(SimpleViewWidget, self).__init__(parent)
        self.colorMap = {}
        self.colorCounter = 0
        
        layout = QVBoxLayout(self)
        
        self.memberView = QLabel(self)
        self.memberView.setAlignment(Qt.AlignHCenter)
        
        sendLayout = QHBoxLayout()
        sendMessageField = QLineEdit(self)
        if hasattr(sendMessageField, "setPlaceholderText"):
            sendMessageField.setPlaceholderText("optional Message")
        lunchButton = LunchButton(parent, sendMessageField)
        
        sendLayout.addWidget(sendMessageField)
        sendLayout.addWidget(lunchButton)
        
        self.msgview = QTextEdit(self)
        self.msgview.setLineWrapMode(QTextEdit.WidgetWidth)
        self.msgview.setReadOnly(True)
        
        layout.addWidget(self.memberView)
        layout.addLayout(sendLayout)
        layout.addWidget(self.msgview)
        
        
        get_notification_center().connectMemberAppended(self.updateWidgets)
        get_notification_center().connectMemberUpdated(self.updateWidgets)
        get_notification_center().connectMemberRemoved(self.updateWidgets)
        get_notification_center().connectMessagePrepended(self.updateWidgets)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateWidgets)
        self.timer.start(60000)
        
    def showEvent(self, showEvent):
        self.updateWidgets()
        
    def getMemberColor(self, peerID):
        if not self.colorMap.has_key(peerID):
            self.colorMap[peerID] = self.colors[self.colorCounter]
            self.colorCounter = (self.colorCounter + 1) % len(self.colors)
        
        return self.colorMap[peerID]
            
    @pyqtSlot(struct_time, object, object)
    @pyqtSlot(object, object)
    @pyqtSlot(object)
    @loggingSlot()
    def updateWidgets(self, _=None, __=None, ___=None):
        if not self.isVisible():
            return True        
        
        members = get_peers().getMembers()
        memText = "%d group members online<br />" % len(members)
        memToolTip = ""

        peers = get_server().getLunchPeers()
        readyMembers = peers.getReadyMembers()
        notReadyMembers = peers.getMembers() - readyMembers
        
        # don't display members with unknown status as ready
        readyMembers = [pID for pID in readyMembers if peers.isPeerReadinessKnown(pID=pID)]
        
        readyText = ", ".join([peers.getDisplayedPeerName(pID=x) for x in readyMembers])
        notReadyText = ", ".join([peers.getDisplayedPeerName(pID=x) for x in notReadyMembers])
        memToolTip += "<span style='color:green'>%s</span><br />" % readyText if len(readyMembers) else ""
        memToolTip += "<span style='color:red'>%s</span>" % notReadyText if len(notReadyMembers) else ""
        
        memText += "<span style='color:green'>%d ready for lunch</span>" % len(readyMembers) if len(readyMembers) else "no one ready for lunch"
        self.memberView.setText(memText)
        self.memberView.setToolTip(memToolTip)
        
        msgTexts = ""
        with get_server().get_messages():
            messages = get_server().get_messages().getAll(time() - (180 * 60))
        for timest, peerID, msg in messages:
            member = get_peers().getDisplayedPeerName(pID=peerID)
            color = self.getMemberColor(peerID)
            msgTexts += "<span style='color:#%s'><b>%s</b> \
                        <i>[%s]</i>: %s</span><br />\n" % (color, member,strftime("%H:%M",timest), msg)
                        
        self.msgview.setHtml(msgTexts)
        
    def create_menu(self, menuBar):
        windowMenu = QMenu("Advanced", menuBar)
        windowMenu.addAction("Manually add an IP", self.addMemberByIP)
        return windowMenu
    
    def addMemberByIP(self):
        hostn, button = QInputDialog.getText(None, "Manually add a member", "In rare cases the lunchinator might not be available to find another user.\n" + 
                             "You can enter an IP/hostname here to explicitly look there. Make sure that the Lunchinator is running on\n" + 
                             "the other machine and that you are in the same group.")
        if button and len(hostn):
            get_server().call_request_info([str(hostn)])
        
    def finish(self):
        try:
            self.timer.timeout.disconnect()
            get_notification_center().disconnectMemberAppended(self.updateWidgets)
            get_notification_center().disconnectMemberUpdated(self.updateWidgets)
            get_notification_center().disconnectMemberRemoved(self.updateWidgets)
            get_notification_center().disconnectMessagePrepended(self.updateWidgets) 
        except:
            getLogger().info("Simple View: was not able to disconnect timer")
        
if __name__ == '__main__':        
    from lunchinator.plugin import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : SimpleViewWidget(window))
