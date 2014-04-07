#@author: Cornelius Ratsch, Hannes Rauhe
#@summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, \
                        QLineEdit
from PyQt4.QtCore import QTimer, Qt
from lunchinator import get_server
from time import mktime,time
from lunchinator.lunch_button import LunchButton
            
class SimpleViewWidget(QWidget):   
    #http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
    colors = ["C44D58","C7F464","4ECDC4","556270","FF6B6B"]
    
    def __init__(self, parent):
        super(SimpleViewWidget, self).__init__(parent)
        self.colorMap = {}
        self.colorCounter = 0
        
        layout = QVBoxLayout(self)
        
        self.memberView = QLabel(self)
        self.memberView.setAlignment(Qt.AlignHCenter)
        
        sendLayout = QHBoxLayout()
        sendMessageField = QLineEdit(self)
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
        self.timer.start(1000)
        
    def getMemberColor(self,addr):
        if not self.colorMap.has_key(addr):
            self.colorMap[addr] = self.colors[self.colorCounter]
            self.colorCounter = (self.colorCounter+1) % len(self.colors)
        
        return self.colorMap[addr]
            
    def updateWidgets(self):
        members = get_server().get_members()
        memText = "%d people online<br />"%len(members)
        memToolTip = ""
        
        readyMembers = []
        notReadyMembers = []
        for m in members:
            if get_server().is_peer_ready(m):
                readyMembers.append(get_server().memberName(m))
            else:
                notReadyMembers.append(get_server().memberName(m))
                
        memToolTip += "<span style='color:green'>%s</span><br />"%", ".join(readyMembers) if len(readyMembers) else ""
        memToolTip += "<span style='color:red'>%s</span>"%", ".join(notReadyMembers) if len(notReadyMembers) else ""
        
        memText += "<span style='color:green'>%d ready for lunch</span>"%len(readyMembers) if len(readyMembers) else "no one ready for lunch"
        self.memberView.setText(memText)
        self.memberView.setToolTip(memToolTip)
        
        msgTexts=""
        for timest,addr,msg in get_server().getMessages(time()-(180*60)):
            member = get_server().memberName(addr)
            color = self.getMemberColor(addr)
            msgTexts+="<span style='color:#%s'><b>%s</b> \
                        <i>[%d sec]</i>: %s</span><br />\n"%(color,member,time()-mktime(timest),msg)
                        
        self.msgview.setHtml(msgTexts)
        
if __name__ == '__main__':        
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : SimpleViewWidget(window))