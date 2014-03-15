#@author: Cornelius Ratsch, Hannes Rauhe
#@summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

from PyQt4.QtGui import QWidget, QVBoxLayout, QTextEdit
from lunchinator import get_server
from time import mktime,time
from lunchinator.lunch_button import LunchButton

class SimpleViewWidget(QWidget):   
    def __init__(self, parent):
        super(SimpleViewWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        
        lunchButton = LunchButton(parent)
        
        msgview = QTextEdit(parent)
        msgview.setLineWrapMode(QTextEdit.WidgetWidth)
        msgview.setReadOnly(True)
        msgTexts=""
        for timest,addr,msg in get_server().getMessages(time()-(180*60)):
            msgTexts+="%s [%d]: %s\n"%(get_server().memberName(addr),time()-mktime(timest),msg)
            
        msgview.setPlainText(msgTexts)
        
        layout.addWidget(lunchButton)
        layout.addWidget(msgview)
        
if __name__ == '__main__':        
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : SimpleViewWidget(window))