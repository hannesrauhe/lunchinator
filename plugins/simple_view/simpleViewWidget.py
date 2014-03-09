#@author: Cornelius Ratsch, Hannes Rauhe
#@summary: This plugin is supposed to be the only one necessary for the core functionality of the lunchinator

import string,os #fixed typo was using
from functools import partial
from PyQt4.QtGui import QWidget, QVBoxLayout, QPushButton, QTextEdit, QSizePolicy, QIcon
from PyQt4.QtCore import QSize
from lunchinator import get_server,get_settings
from time import mktime,time

class simpleViewWidget(QWidget):   
    
    def callForLunch(self):
        get_server().call("lunch")
    
    def __init__(self, parent):
        super(simpleViewWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        
        lunchIcon = QIcon(os.path.join(get_settings().get_lunchdir(), "images", "lunch.svg"))
        lunchButton = QPushButton(parent)
        lunchButton.setIcon(lunchIcon)
        lunchButton.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        lunchButton.setIconSize(QSize(64, 64))
        lunchButton.clicked.connect(self.callForLunch)
        
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
    iface_gui_plugin.run_standalone(lambda window : simpleViewWidget(window))