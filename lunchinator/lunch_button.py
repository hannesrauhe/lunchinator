from PyQt4.QtGui import QPushButton, QSizePolicy, QIcon
from PyQt4.QtCore import QSize
from lunchinator import get_settings, get_server
import os
    
class LunchButton(QPushButton):
    def __init__(self, parent):
        super(LunchButton, self).__init__(parent)
        
        lunchIcon = QIcon(os.path.join(get_settings().get_lunchdir(), "images", "lunch.png"))
        self.setIcon(lunchIcon)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setIconSize(QSize(64, 64))
        self.clicked.connect(self.callForLunch)
        
    def callForLunch(self):
        get_server().call("lunch")
