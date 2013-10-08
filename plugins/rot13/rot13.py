import string #fixed typo was using
from PyQt4.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QSizePolicy

class rot13box(QWidget):
    def __init__(self, parent):
        super(rot13box, self).__init__(parent)
        self.entry = None
        self.but = None
        self.buffer = None
        
        layout = QVBoxLayout(self)
        
        self.entry = QLineEdit(self)
        self.but = QPushButton("ROT13", self)
        if self.buffer is not None:
            self.encodeText(self.buffer)
        
        layout.addWidget(self.entry)
        
        butLayout = QHBoxLayout()
        butLayout.addWidget(self.but)
        butLayout.addWidget(QWidget(self), 1)
        butLayout.setSpacing(0)
        layout.addLayout(butLayout)
        
        self.but.clicked.connect(self.enc)
        
        self.setMaximumHeight(self.sizeHint().height())
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
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
        
    