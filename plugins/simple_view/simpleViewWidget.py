#@author: Cornelius Ratsch, Hannes Rauhe
#@summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

from PyQt4.QtGui import QWidget, QVBoxLayout, QTextEdit
from PyQt4.QtCore import QTimer
from lunchinator import get_server
from time import mktime,time
from lunchinator.lunch_button import LunchButton

class SimpleViewWidget(QWidget):   
    #http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
    colors = ["C44D58","FF6B6B","C7F464","4ECDC4","556270"]
    
    def __init__(self, parent):
        super(SimpleViewWidget, self).__init__(parent)
        self.colorMap = {}
        self.colorCounter = 0
        
        layout = QVBoxLayout(self)
        
        self.memberView = QTextEdit(parent)
        self.memberView.setLineWrapMode(QTextEdit.WidgetWidth)
        self.memberView.setReadOnly(True)
        
        lunchButton = LunchButton(parent)
        
        self.msgview = QTextEdit(parent)
        self.msgview.setLineWrapMode(QTextEdit.WidgetWidth)
        self.msgview.setReadOnly(True)
        
        layout.addWidget(self.memberView)
        layout.addWidget(lunchButton)
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
        memText = "%d people online"%len(members)
        self.memberView.setHtml(memText)
        
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