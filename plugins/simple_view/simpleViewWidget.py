# @author: Cornelius Ratsch, Hannes Rauhe
# @summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, \
                        QLineEdit, QMenu, QInputDialog
from PyQt4.QtCore import QTimer, Qt
from lunchinator import get_server, get_peers, log_info, get_notification_center
from time import mktime, time
from lunchinator.lunch_button import LunchButton
            
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
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateWidgets)
        self.timer.start(60000)
        
    def activate(self):
        super(SimpleViewWidget, self).activate()
        
        get_notification_center().connectMemberAppendedSignal(self.updateWidgets)
        get_notification_center().connectMemberUpdatedSignal(self.updateWidgets)
        get_notification_center().connectMemberRemovedSignal(self.updateWidgets)
        get_notification_center().connectMessagePrepended(self.updateWidgets)
        
    def deactivate(self):
        get_notification_center().disconnectMemberAppendedSignal(self.updateWidgets)
        get_notification_center().disconnectMemberUpdatedSignal(self.updateWidgets)
        get_notification_center().disconnectMemberRemovedSignal(self.updateWidgets)
        get_notification_center().disconnectMessagePrepended(self.updateWidgets)
        
        super(SimpleViewWidget, self).deactivate()
        
    def showEvent(self, showEvent):
        self.updateWidgets()
        
    def getMemberColor(self, peerID):
        if not self.colorMap.has_key(peerID):
            self.colorMap[peerID] = self.colors[self.colorCounter]
            self.colorCounter = (self.colorCounter + 1) % len(self.colors)
        
        return self.colorMap[peerID]
            
    def updateWidgets(self):
        if not self.isVisible():
            return True        
        
        members = get_peers().getMembers()
        memText = "%d people online<br />" % len(members)
        memToolTip = ""

        peers = get_server().getLunchPeers()
        readyMembers = peers.getReadyMembers()
        notReadyMembers = peers.getMembers() - readyMembers
                
        memToolTip += "<span style='color:green'>%s</span><br />" % ", ".join(readyMembers) if len(readyMembers) else ""
        memToolTip += "<span style='color:red'>%s</span>" % ", ".join(notReadyMembers) if len(notReadyMembers) else ""
        
        memText += "<span style='color:green'>%d ready for lunch</span>" % len(readyMembers) if len(readyMembers) else "no one ready for lunch"
        self.memberView.setText(memText)
        self.memberView.setToolTip(memToolTip)
        
        msgTexts = ""
        for timest, addr, msg in get_server().getMessages(time() - (180 * 60)):
            peerID = get_peers().getPeerID(addr)
            member = get_peers().getPeerName(peerID)
            color = self.getMemberColor(peerID)
            msgTexts += "<span style='color:#%s'><b>%s</b> \
                        <i>[%d sec]</i>: %s</span><br />\n" % (color, member, time() - mktime(timest), msg)
                        
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
        except:
            log_info("Simple View: was not able to disconnect timer")
        
if __name__ == '__main__':        
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : SimpleViewWidget(window))
