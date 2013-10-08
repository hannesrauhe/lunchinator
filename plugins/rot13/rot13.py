import string #fixed typo was using
from PyQt4.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QImage, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import Qt
from lunchinator import log_exception

class rot13box(QWidget):
    def __init__(self, parent, picture_file = None):
        super(rot13box, self).__init__(parent)
        self.entry = None
        self.but = None
        self.buffer = None
        self.picture_file = None        
        self.additional_widget = QLabel()
        self.maxwidth=400
        self.maxheight=400
        self.show_pic=False
        
        layout = QVBoxLayout(self)
        self.picture_file = picture_file
        
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
        layout.addWidget(self.additional_widget, 1)
        
        self.but.clicked.connect(self.enc)
        
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
        if self.picture_file:
            if self.show_pic:
                try:
                    qtimage = QImage(self.picture_file)
                    if qtimage.width() > 0 and qtimage.height() > 0:
                        width = self.maxwidth
                        height = qtimage.height()*self.maxwidth/qtimage.width()
                        if height>self.maxheight:
                            height = self.maxheight
                            width = qtimage.width()*self.maxheight/qtimage.height()
                        qtimage = qtimage.scaled(width, height, aspectRatioMode=Qt.IgnoreAspectRatio, transformMode=Qt.SmoothTransformation)
                        self.additional_widget.setPixmap(QPixmap.fromImage(qtimage))
                except:
                    log_exception("Error creating image label")
            else:
                self.additional_widget.setPixmap(QPixmap())
            self.show_pic = not self.show_pic
        
    