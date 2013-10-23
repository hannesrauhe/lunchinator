from PyQt4.QtGui import QWidget, QVBoxLayout, QPushButton, QTextEdit, QSizePolicy, QGroupBox
from PyQt4.QtCore import QSize
from lunchinator import get_server
from bug_report.bug_reports_widget import BugReportsWidget

class bug_report_gui(QWidget):
    PREFERRED_WIDTH  = 400
    PREFERRED_HEIGHT = 150
    
    def __init__(self, parent, mt):
        super(bug_report_gui, self).__init__(parent)
        
        self.entry = QTextEdit(parent)
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        
        self.but = QPushButton("Send Report", parent)
        self.but.clicked.connect(self.send_report)
        
        layout = QVBoxLayout(self)
        self.bugReportsWidget = BugReportsWidget(self, mt)
        layout.addWidget(self.bugReportsWidget, 1)
        
        groupBox = QGroupBox("Create legacy bug report", self)
        groupBoxLayout = QVBoxLayout(groupBox)
        groupBoxLayout.addWidget(self.entry)
        groupBoxLayout.addWidget(self.but)
        layout.addWidget(groupBox)
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        
    def repoChanged(self):
        self.bugReportsWidget.repoChanged()
        
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
    class maintainer_wrapper(object):
        reports = []
        options = {u"github_token":"", u"repo_user":u"hannesrauhe", u"repo_name":u"lunchinator"}
        def __init__(self):
            tokenPath = os.path.join(os.path.expanduser("~"), ".github_token")
            if os.path.exists(tokenPath):
                with open(tokenPath) as tokenFile:
                    token = tokenFile.readline()
                    self.options[u"github_token"] = token
            
        def getBugsFromDB(self, _):
            return []
        
        def set_option(self, option, newValue, convert = True):
            print "set %s to '%s' (%s), convert: %s" % (option, newValue, type(newValue), convert)
        
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : bug_report_gui(window, maintainer_wrapper()))