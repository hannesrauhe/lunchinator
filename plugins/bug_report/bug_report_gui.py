from PyQt4.QtGui import QLabel, QWidget, QVBoxLayout, QPushButton, QTextEdit, QSizePolicy
from PyQt4.QtCore import QSize
from lunchinator import get_server

class bug_report_gui(QWidget):
    PREFERRED_WIDTH  = 400
    PREFERRED_HEIGHT = 150
    
    def __init__(self, parent):
        super(bug_report_gui, self).__init__(parent)
        
        self.entry = QTextEdit(parent)
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        
        self.but = QPushButton("Send Report", parent)
        self.but.clicked.connect(self.send_report)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Describe your problem:", parent))
        layout.addWidget(self.entry)
        layout.addWidget(self.but)
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        
    def send_report(self):
        plainText = self.entry.toPlainText()
        if get_server() and len(plainText):
            get_server().call("HELO_BUGREPORT_DESCR %s"%plainText)
        else:
            print "HELO_BUGREPORT_DESCR %s"%plainText
            
        self.entry.setPlainText("")
            
    def sizeHint(self):
        return QSize(self.PREFERRED_WIDTH, self.PREFERRED_HEIGHT)

if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(bug_report_gui(None))