import string #fixed typo was using
from PyQt4.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit
from PyQt4.QtCore import QObject

class rot13box(QObject):
    def __init__(self, parent):
        super(rot13box, self).__init__(parent)
        self.entry = None
        self.but = None
        self.add_widget = None
        self.buffer = None
        
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
        if self.add_widget:
            self.add_widget.show()
        
    def create_widget(self,parent,additional_widget=None):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.entry = QLineEdit(widget)
        self.but = QPushButton("ROT13", widget)
        if self.buffer is not None:
            self.encodeText(self.buffer)
        
        layout.addWidget(self.entry)
        
        butLayout = QHBoxLayout()
        butLayout.addWidget(self.but)
        butLayout.addWidget(QWidget(widget), 1)
        butLayout.setSpacing(0)
        layout.addLayout(butLayout)
        
        if additional_widget:
            self.add_widget = additional_widget
            layout.addWidget(additional_widget, 1)
        else:
            layout.addWidget(QWidget(parent), 1)
        
        self.but.clicked.connect(self.enc)
        return widget
    
if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(rot13box(None))
    