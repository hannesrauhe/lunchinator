from PyQt4.QtGui import QGridLayout, QWidget, QLabel
from lunchinator import get_settings

class SetupGui(QWidget):
    def __init__(self, parent, logger):
        super(SetupGui, self).__init__(parent)
        self.logger = logger
        
        lay = QGridLayout(self)
        self.label = QLabel("Please make sure that secrets and keys in settings are correct")
        lay.addWidget(self.label, 0, 0, 1, 2)
        