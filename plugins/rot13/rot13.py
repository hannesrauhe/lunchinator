import string #fixed typo was using
from functools import partial
from PyQt4.QtGui import QWidget, QHBoxLayout, QPushButton, QLineEdit, QSizePolicy, QToolButton, QMenu
from lunchinator import get_server

class rot13box(QWidget):
    def __init__(self, parent):
        super(rot13box, self).__init__(parent)
        self.entry = None
        self.but = None
        self.buffer = None
        
        self.entry = QLineEdit(self)
        self.but = QPushButton("ROT13", self)
        if self.buffer is not None:
            self.encodeText(self.buffer)
        
        
        layout = QHBoxLayout(self)
        grabButton = QToolButton(parent)
        grabButton.setText("Msg")
        grabButton.setMinimumHeight(self.but.sizeHint().height())
        self.msgMenu = QMenu(grabButton)
        self.msgMenu.aboutToShow.connect(self.updateMsgMenu)
        grabButton.setMenu(self.msgMenu)
        grabButton.setPopupMode(QToolButton.InstantPopup)
        #grabButton.clicked.connect(self.grabMessage)
        
        layout.addWidget(grabButton)
        layout.addWidget(self.entry)
        layout.addWidget(self.but)
        
        self.but.clicked.connect(self.enc)
        
        self.setMaximumHeight(self.sizeHint().height())
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
    def updateMsgMenu(self):
        self.msgMenu.clear()
        get_server().lockMessages()
        try:
            for i in range(min(10, len(get_server().getMessages()))):
                self.msgMenu.addAction(get_server().getMessages()[i][2], partial(self.encodeText, get_server().getMessages()[i][2]))
        finally:
            get_server().releaseMessages()
        
    def grabMessage(self):
        self.encodeText(get_server().getMessage(0)[2])
        
    def encodeText(self,text):
        if self.entry is not None:
            self.entry.setText(text)
            self.enc()
        else:
            self.buffer = text
        
    def enc(self):        
        rot13 = string.maketrans( 
            u"ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz", 
            u"NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")
        plain = self.entry.text()
        if plain:
            self.entry.setText(string.translate(str(plain.toUtf8()), rot13))
        
    