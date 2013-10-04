import time,codecs,os,tarfile
from datetime import datetime
from functools import partial
from lunchinator import get_server, get_settings, convert_string, log_exception
from lunchinator.table_models import ExtendedMembersModel
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QTreeView, QStandardItemModel, QStandardItem, QSpinBox, QTabWidget, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem
from PyQt4.QtCore import QObject, pyqtSlot, QThread, Qt, QStringList

class maintainer_gui(QObject):
    def __init__(self,parent,mt):
        super(maintainer_gui, self).__init__(parent)
        self.entry = None
        self.but = None
        self.info_table = None
        self.mt = mt
        self.dropdown_members = None
        self.dropdown_members_dict = None
        self.dropdown_members_model = None
        self.visible = False
        self.sendMessageButton = None
        self.update_button = None
        self.requestLogsButton = None
        
    @pyqtSlot(QThread, unicode)
    def cb_log_transfer_success(self, thread, path):
        path = convert_string(path)
        if path.endswith(".tgz"):
            # extract
            # TODO remove all log files
            with tarfile.open(path, 'r:gz') as tarContent:
                tarContent.extractall(os.path.dirname(path))
        else:
            # log comes from old version
            os.rename(path, os.path.dirname(path) + os.sep + "0.log")
            
        if not self.visible:
            return False
        
        self.updateLogList()
        thread.deleteLater()
    
    @pyqtSlot(QThread)
    def cb_log_transfer_error(self, thread):
        if not self.visible:
            return False
        self.log_area.setText("Error while getting log")
        thread.deleteLater()
        
    def update_reports(self):
        mode="open"
        self.bug_reports = self.mt.getBugsFromDB(mode)
        
    def display_report(self):
        if self.dropdown_reports.currentIndex()>=0:
            self.entry.setText(str(self.bug_reports[self.dropdown_reports.currentIndex()][2]))
            
    def close_report(self):
        rep_nr = self.dropdown_reports.currentIndex()
        if rep_nr>=0:
            get_server().call("HELO_BUGREPORT_CLOSE %s %s"%(self.bug_reports[rep_nr][0],self.bug_reports[rep_nr][1]))        
            del self.bug_reports[rep_nr]
            self.dropdown_reports.removeItem(rep_nr)
            self.dropdown_reports.setCurrentIndex(0)
            self.display_report()

    def get_selected_log_member(self):
        member = str(self.dropdown_members.currentText())
        if member == None or len(member) == 0:
            return None
        
        if "(" in member:
            # member contains name, extract IP
            member = member[member.rfind("(")+1:member.rfind(")")]
            
        return member
    
    def request_log(self):
        member = self.get_selected_log_member()
        if member != None:
            self.updateLogList("Requesting log from %s..." % member)
            # send number 0 for backwards compatibility
            get_server().call("HELO_REQUEST_LOGFILE %s 0"%(get_settings().get_tcp_port()),member)
        else:
            self.log_area.setText("No Member selected!")
            
    def request_update(self):
        member = self.get_selected_log_member()
        if member != None:
            get_server().call("HELO_UPDATE from GUI",member)
            
    def create_reports_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.entry = QTextEdit(widget)
        
        self.update_reports()
        self.dropdown_reports = QComboBox(widget)
        for r in self.bug_reports:
            self.dropdown_reports.addItem("%s - %s"%(time.strftime("%a, %d %b %Y %H:%M:%S",time.localtime(r[0])),r[1]))
        self.dropdown_reports.setCurrentIndex(0)
        self.display_report()
        self.close_report_btn = QPushButton("Close Bug", widget)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_reports)
        topLayout.addWidget(self.close_report_btn)
        topLayout.addWidget(QWidget(widget), 1)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Description:", widget))
        
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        self.entry.setReadOnly(True)
        layout.addWidget(self.entry)
                
        self.dropdown_reports.currentIndexChanged.connect(self.display_report)
        self.close_report_btn.clicked.connect(self.close_report)
        
        return widget
    
    def create_info_table_widget(self, parent):
        self.info_table = QTreeView(parent)
        self.info_table.setAlternatingRowColors(True)
        self.info_table.setModel(ExtendedMembersModel(get_server()))
        return self.info_table
    
    def get_dropdown_member_text(self, m_ip, m_name):
        if m_ip == m_name:
            return m_ip
        else:
            return "%s (%s)" % (m_name.strip(), m_ip.strip())
    
    def update_dropdown_members(self):
        if self.dropdown_members_model == None:
            return
        for m_ip in get_server().get_members():
            m_name = get_server().memberName(m_ip)
            if not m_ip in self.dropdown_members_dict:
                # is new ip, append to the end
                self.dropdown_members_dict[m_ip] = (self.dropdown_members_model.rowCount(), m_name)
                self.dropdown_members_model.appendRow(QStandardItem(self.get_dropdown_member_text(m_ip, m_name)))
            else:
                #is already present, check if new information is available
                info = self.dropdown_members_dict[m_ip]
                if m_name != info[1]:
                    #name has changed
                    anItem = self.dropdown_members_model.item(info[0], column=0)
                    anItem.setText(self.get_dropdown_member_text(m_ip, m_name))
                    self.dropdown_members_dict[m_ip] = (info[0], m_name)
                
    def listLogFilesForMember(self, member):
        logDir = "%s/logs/%s" % (get_settings().get_main_config_dir(), member)
        files = []
        if os.path.exists(logDir) and os.path.isdir(logDir):
            for f in os.listdir(logDir):
                if f.endswith(".log") and not os.path.isdir(f):
                    files.append(f)
                    
        return files

    def numLogFilesForMember(self, member):
        return len(self.listLogFilesForMember(member))
                
    def updateLogList(self, text = None):
        selectedMember = self.get_selected_log_member()
        self.log_tree_view.clear()
        if text != None or selectedMember == None or self.numLogFilesForMember(selectedMember) == 0:
            self.log_tree_view.addTopLevelItem(QTreeWidgetItem(self.log_tree_view, QStringList("No logs available." if text is None else text)))
            self.log_tree_view.setSelectionMode(QTreeWidget.NoSelection)
        else:
            logPath = "%s/logs/%s/" % (get_settings().get_main_config_dir(), selectedMember)
            for logFile in self.listLogFilesForMember(selectedMember):
                timestamp = datetime.fromtimestamp(os.path.getmtime(logPath + logFile)).strftime("%Y-%m-%d %H:%M:%S")
                self.log_tree_view.addTopLevelItem(QTreeWidgetItem(self.log_tree_view, QStringList(timestamp)))
                self.log_tree_view.setSelectionMode(QTreeWidget.SingleSelection)
        self.displaySelectedLogfile()
    
    def getSelectedLogContent(self):
        member = self.get_selected_log_member()
        if member is None:
            return "No Log selected."
        selection = self.log_tree_view.selectedIndexes()
        if len(selection) is 0:
            return "No Log selected."
        logIndex = selection[0].row()
        
        logPath = "%s/logs/%s/%s.log" % (get_settings().get_main_config_dir(), member, logIndex)
        if not os.path.exists(logPath):
            return "No Log selected."
        
        fcontent = ""
        try:
            with codecs.open(logPath,"r",'utf8') as fhandler:
                fcontent = fhandler.read()
        except Exception as e:
            log_exception("Error reading file")
            fcontent = "Error reading file: %s"%str(e)
        return fcontent
    
    def displaySelectedLogfile(self):
        self.log_area.setText(self.getSelectedLogContent())
        
    def memberSelectionChanged(self):
        self.updateLogList()
        isMemberSelected = self.get_selected_log_member() != None
        self.sendMessageButton.setEnabled(isMemberSelected)
        self.update_button.setEnabled(isMemberSelected)
        self.requestLogsButton.setEnabled(isMemberSelected)
        
    def sendMessageToMember(self, lineEdit):
        selectedMember = self.get_selected_log_member()
        if selectedMember != None:
            get_server().call(convert_string(lineEdit.text()),client=selectedMember)
        
    def create_members_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setSpacing(0)
        
        self.dropdown_members_dict = {}
        self.dropdown_members_model = QStandardItemModel()
        self.dropdown_members_model.appendRow(QStandardItem(""))
        self.dropdown_members = QComboBox(widget)
        self.dropdown_members.setModel(self.dropdown_members_model)
        self.update_dropdown_members()
        
        self.update_button = QPushButton("Send Update Command", widget)

        topLayout = QHBoxLayout()
        topLayout.setSpacing(10)
        topLayout.addWidget(self.dropdown_members, 1)
        topLayout.addWidget(self.update_button)
        self.requestLogsButton = QPushButton("Request Logfiles", widget)
        topLayout.addWidget(self.requestLogsButton)
        layout.addLayout(topLayout)
        
        layout.addWidget(QLabel("Send Message:", widget))
        
        sendMessageLayout = QHBoxLayout()
        sendMessageLayout.setSpacing(10)
        messageInput = QLineEdit(widget)
        self.sendMessageButton = QPushButton("Send", widget)
        sendMessageLayout.addWidget(messageInput, 1)
        sendMessageLayout.addWidget(self.sendMessageButton)
        layout.addLayout(sendMessageLayout)
        
        layout.addWidget(QLabel("Log files:", widget))
        logSplitter = QSplitter(Qt.Horizontal, widget)
        
        self.log_tree_view = QTreeWidget(logSplitter)
        self.log_tree_view.setAlternatingRowColors(True)
        self.log_tree_view.setColumnCount(1)
        self.log_tree_view.setHeaderHidden(True)
        self.log_tree_view.setItemsExpandable(False)
        self.log_tree_view.setIndentation(0)
        
        logSplitter.addWidget(self.log_tree_view)
        
        self.log_area = QTextEdit(widget)
        self.log_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_area.setReadOnly(True)
        logSplitter.addWidget(self.log_area)
        
        logSplitter.setStretchFactor(0, 0)
        logSplitter.setStretchFactor(1, 1)
        
        layout.addWidget(logSplitter, 1)
        
        self.memberSelectionChanged()
        self.log_tree_view.selectionModel().selectionChanged.connect(self.displaySelectedLogfile)
        self.dropdown_members.currentIndexChanged.connect(self.memberSelectionChanged)
        self.update_button.clicked.connect(self.request_update)
        self.requestLogsButton.clicked.connect(self.request_log)
        self.sendMessageButton.clicked.connect(partial(self.sendMessageToMember, messageInput))
        messageInput.returnPressed.connect(partial(self.sendMessageToMember, messageInput))
        
        return widget
    
    def create_widget(self, parent):
        nb = QTabWidget(parent)
        nb.setTabPosition(QTabWidget.West)
        
        reports_widget = self.create_reports_widget(nb)
        logs_widget = self.create_members_widget(nb)
        info_table_widget = self.create_info_table_widget(nb)
        
        nb.addTab(reports_widget, "Bug Reports")        
        nb.addTab(logs_widget, "Members")        
        nb.addTab(info_table_widget, "Info")
        
        nb.setCurrentIndex(0)
        self.visible = True
        
        return nb
    
    def destroy_widget(self):
        self.visible = False
    
class maintainer_wrapper:
    reports = []
    def getBugsFromDB(self, _):
        return []
    
if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(maintainer_gui(None, maintainer_wrapper()))
    