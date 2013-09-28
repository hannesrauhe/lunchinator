from PyQt4.QtGui import QLabel, QWidget, QVBoxLayout, QPushButton, QTextEdit
from lunchinator import get_server

class bug_report_gui(object):
    def __init__(self):
        self.entry = None
        self.but = None
        
    def send_report(self):
        plainText = self.entry.toPlainText()
        if get_server() and len(plainText):
            get_server().call("HELO_BUGREPORT_DESCR %s"%plainText)
        else:
            print "HELO_BUGREPORT_DESCR %s"%plainText
            
        self.entry.setPlainText("")
            
    def create_widget(self, parent):
        self.entry = QTextEdit(parent)
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        
        self.but = QPushButton("Send Report", parent)
        self.but.clicked.connect(self.send_report)
        
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Describe your problem:", parent))
        layout.addWidget(self.entry)
        layout.addWidget(self.but)
        return widget

if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(bug_report_gui())