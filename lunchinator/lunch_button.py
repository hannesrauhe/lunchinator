from PyQt4.QtGui import QPushButton, QSizePolicy, QIcon
from PyQt4.QtCore import QSize
from lunchinator import get_settings, get_server, convert_string
    
class LunchButton(QPushButton):
    def __init__(self, parent, msgfield=None):
        super(LunchButton, self).__init__(parent)
        
        lunchIcon = QIcon(get_settings().get_resource("images", "lunchinator.png"))
        self.setIcon(lunchIcon)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setIconSize(QSize(64, 64))
        self.clicked.connect(self.callForLunch)
        self.sendMessageField = msgfield
        
    def callForLunch(self):
        optmsg = ""
        if self.sendMessageField:
            optmsg = convert_string(self.sendMessageField.text())
            self.sendMessageField.clear()
            
        if len(optmsg):
            get_server().call(optmsg)
        else:
            get_server().call(get_settings().get_lunch_trigger())
