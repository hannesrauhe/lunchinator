import time,codecs,os,tarfile,shutil,copy,sip,contextlib
from datetime import datetime
from functools import partial
from lunchinator import get_server, get_settings, convert_string, log_exception,\
    log_debug, getLogLineTime, log_warning
from lunchinator.table_models import ExtendedMembersModel
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QTreeView, QStandardItemModel, QStandardItem, QTabWidget, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QSortFilterProxyModel
from PyQt4.QtCore import QObject, pyqtSlot, QThread, Qt, QStringList, QVariant, QTimer, Qt
from lunchinator.lunch_datathread_qt import DataReceiverThread

class maintainer_gui(QObject):
    LOG_REQUEST_TIMEOUT = 10 # 10 seconds until request is invalid
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
        self.logRequests = {}
        
    def listLogfiles(self, basePath, sort = None):
        if sort is None:
            sort = lambda aFile : -self.getLogNumber(aFile)
        logList = [basePath + os.sep + aFile for aFile in os.listdir(basePath) if aFile.endswith(".log") and not os.path.isdir(basePath + os.sep + aFile)]
        return sorted(logList, key = sort)
    
    def getNumLogsToKeep(self, oldLogFiles, newLogFiles, logOffset):
        oldestNew = None
        for aLogFile in newLogFiles:
            oldestNew, _ = self.getLogDates(aLogFile)
            if oldestNew != None:
                break
        
        if oldestNew == None:
            # new new log file contains timestamps (they are probably all empty)
            return len(oldLogFiles)
        
        numToKeep = 0
        while numToKeep < len(oldLogFiles) - logOffset:
            curTime, _ = self.getLogDates(oldLogFiles[numToKeep])
            if curTime == None or curTime < oldestNew:
                # keep empty log files
                numToKeep = numToKeep + 1
            else:
                break
        return numToKeep
        
    def getLogDates(self, aLogFile):
        with codecs.open(aLogFile, 'rb', 'utf-8') as logContent:
            logLines = logContent.readlines()
            firstDate = None
            for aLine in logLines:
                firstDate = getLogLineTime(aLine)
                if firstDate != None:
                    break
                
            lastDate = None
            for aLine in reversed(logLines):
                lastDate = getLogLineTime(aLine)
                if lastDate != None:
                    break
        
            return firstDate, lastDate
        
    def getLogNumber(self, aLogFile):
        aLogFile = os.path.basename(aLogFile)
        try:
            return int(aLogFile[:aLogFile.rfind(".")])
        except:
            return -1
        
    def shiftLogFiles(self, oldLogFiles, numToKeep, shift, logOffset):
        renamedLogfiles = []
        for index, aFile in enumerate(oldLogFiles):
            logNum = self.getLogNumber(aFile)
            if logNum < logOffset:
                # don't touch up-to-date logs
                break
            if index < numToKeep:
                newName = "%s%s%d.log" % (os.path.dirname(aFile), os.sep, logNum + shift)
                renamedLogfiles.append((len(oldLogFiles) - index - 1, aFile, newName))
                os.rename(aFile, newName)
            else:
                os.remove(aFile)
        return renamedLogfiles
    
    def handleNewLogFiles(self, basePath, tmpPath, logOffset = 0):
        oldLogFiles = self.listLogfiles(basePath)
        newLogFiles = self.listLogfiles(tmpPath)
        
        #check how many log files are actually new
        numToKeep = self.getNumLogsToKeep(oldLogFiles, newLogFiles, logOffset)
        
        #rename / remove old log files to make room for the new ones
        numNew = len(newLogFiles) - (len(oldLogFiles) - logOffset - numToKeep)
        renamedLogfiles = self.shiftLogFiles(oldLogFiles, numToKeep, numNew, logOffset)
        
        # move new log files
        addedLogfiles = []
        for index, aLogFile in enumerate(reversed(newLogFiles)):
            shutil.move(aLogFile, basePath)
            if index < numNew:
                addedLogfiles.append((index + logOffset, "%s%s%s" % (basePath, os.sep, os.path.basename(aLogFile))))
        shutil.rmtree(tmpPath, True)
        
        return numNew, addedLogfiles, renamedLogfiles
    
    def requestFinished(self):
        self.requestLogsButton.setEnabled(True)
        self.dropdown_members.setEnabled(True)
    
    @pyqtSlot(QThread, unicode)
    def cb_log_transfer_success(self, thread, path):
        path = convert_string(path)
        
        basePath = os.path.dirname(path)
        tmpPath = basePath + os.sep + "tmp"
        if not os.path.exists(tmpPath):
            os.makedirs(tmpPath)

        logsAdded = []   
        if path.endswith(".tgz"):
            #extract received log files
            with contextlib.closing(tarfile.open(path, 'r:gz')) as tarContent:
                tarContent.extractall(tmpPath)
            _, logsAdded, logsRenamed = self.handleNewLogFiles(basePath, tmpPath)
            self.requestFinished()
        else:
            # log comes from old version
            logNum = 0
            if thread.sender in self.logRequests:
                logNum, requestTime = self.logRequests[thread.sender]
                now = datetime.now()
                td = now - requestTime
                tdSeconds = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
                if tdSeconds > self.LOG_REQUEST_TIMEOUT:
                    # request timed out or was finished already
                    logNum = 0
            
            shutil.move(path, "%s%s%d.log" % (tmpPath, os.sep, logNum))
            
            numNew, logsAdded, logsRenamed = self.handleNewLogFiles(basePath, tmpPath, logNum)
            if numNew > 0 and logNum < 9:
                # there might be more new ones
                self.logRequests[thread.sender] = (logNum + 1, datetime.now())
                log_debug("log seems to be new, another!!!")
                logsAdded.append((logNum + 1, None))
                self.request_log(thread.sender, logNum + 1)
            elif thread.sender in self.logRequests:
                # request finished
                del self.logRequests[thread.sender]
                self.requestFinished()
            else:
                self.requestFinished()
            
        if not self.visible:
            return False
        
        if len(logsAdded) > 0 or len(logsRenamed) > 0:
            self.updateLogList(logsAdded, logsRenamed)
    
    @pyqtSlot(QThread)
    def cb_log_transfer_error(self, _thread):
        if not self.visible:
            return False
        self.log_area.setText("Error while getting log")
        self.requestFinished()
        
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
    
    def request_log(self, member = None, logNum = 0):
        if member is None:
            member = self.get_selected_log_member()
        if member != None:
            log_debug("Requesting log %d from %s" % (logNum, member))
            get_server().call("HELO_REQUEST_LOGFILE %s %d"%(DataReceiverThread.getOpenPort(category="log%s"%member), logNum), member)
        else:
            self.log_area.setText("No Member selected!")
            
    @pyqtSlot()
    def requestLogClicked(self):
        self.requestLogsButton.setEnabled(False)
        self.dropdown_members.setEnabled(False)
        self.updateLogList([(0, None)])
        self.request_log()
            
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
        self.info_table.setSortingEnabled(True)
        self.info_table.setHeaderHidden(False)
        self.info_table.setAlternatingRowColors(True)
        self.info_table.setIndentation(0)
        
        self.info_table_model = ExtendedMembersModel(get_server())
        proxyModel = QSortFilterProxyModel(self.info_table)
        proxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxyModel.setDynamicSortFilter(True)
        proxyModel.setSourceModel(self.info_table_model)
        
        self.info_table.setModel(proxyModel)
        return self.info_table
    
    def get_dropdown_member_text(self, m_ip, m_name):
        if m_ip == m_name:
            return m_ip
        else:
            return "%s (%s)" % (m_name.strip(), m_ip.strip())
    
    def update_dropdown_members(self):
        self.updateMemberInformation()
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
        if not os.path.exists(logDir):
            return []
        return self.listLogfiles(logDir)

    def numLogFilesForMember(self, member):
        return len(self.listLogFilesForMember(member))
            
    def requestTimedOut(self, item):
        if not sip.isdeleted(item) and item != None and item.data(0, Qt.UserRole) == None:
            self.log_tree_view.takeTopLevelItem(self.log_tree_view.indexFromItem(item).row())
            self.requestFinished()
             
    def initializeLogItem(self, item, logFile):
        firstDate, lastDate = self.getLogDates(logFile)
        text = None
        tooltip = None
        if firstDate != None:
            text = firstDate.strftime("%Y-%m-%d %H:%M:%S")
            tooltip = u"File: %s\nFirst entry: %s\nLast entry: %s" % (logFile, firstDate.strftime("%Y-%m-%d %H:%M:%S"), lastDate.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            timestamp = datetime.fromtimestamp(os.path.getmtime(logFile)).strftime("%Y-%m-%d %H:%M:%S")
            text = u"%s" % os.path.basename(logFile)
            tooltip = u"File:%s\nModification Date: %s" % (logFile, timestamp)
        if tooltip != None:
            item.setData(0, Qt.ToolTipRole, QVariant(tooltip)) 
        item.setData(0, Qt.UserRole, logFile)
        item.setData(0, Qt.DisplayRole, QVariant(text))
                 
       
    def updateLogList(self, logsAdded = None, logsRenamed = None):
        selectedMember = self.get_selected_log_member()

        if logsAdded == None:
            self.log_tree_view.clear()
            logsAdded = []
            for index, logFile in enumerate(reversed(self.listLogFilesForMember(selectedMember))):
                logsAdded.append((index, logFile))
            if len(logsAdded) == 0:
                self.log_tree_view.clear()
                self.log_tree_view.addTopLevelItem(QTreeWidgetItem(self.log_tree_view, QStringList("No logs available.")))
                self.log_tree_view.setSelectionMode(QTreeWidget.NoSelection)
                return
            
        if logsRenamed != None:
            for index, oldName, newName in logsRenamed:
                # index + 1 because of the "requesting" item
                item = self.log_tree_view.topLevelItem(index + 1)
                if item != None:
                    itemLogFile = convert_string(item.data(0, Qt.UserRole).toString())
                    if itemLogFile != oldName:
                        log_warning("index does not correspond to item in list:\n\t%s\n\t%s" % (itemLogFile, oldName))
                    self.initializeLogItem(item, newName)
            
        if len(logsAdded) == 0:
            self.log_tree_view.takeTopLevelItem(0)
        else:
            for index, logFile in logsAdded:
                oldItem = self.log_tree_view.topLevelItem(index)
                item = None
                if oldItem != None and oldItem.data(0, Qt.UserRole) == None:
                    # requested item has been received
                    item = oldItem
                else:
                    item = QTreeWidgetItem()
                    oldItem = None
                
                if logFile == None:
                    item.setData(0, Qt.DisplayRole, QVariant("Requesting..."))
                    QTimer.singleShot(6000, partial(self.requestTimedOut, item)) 
                else:
                    self.initializeLogItem(item, logFile)
                
                if oldItem is None:
                    # else, the old item is being modified
                    self.log_tree_view.insertTopLevelItem(index, item)
                self.log_tree_view.setSelectionMode(QTreeWidget.SingleSelection)
        self.displaySelectedLogfile()
    
    def getSelectedLogContent(self):
        member = self.get_selected_log_member()
        if member is None:
            return "No Log selected."
        selection = self.log_tree_view.selectedIndexes()
        if len(selection) is 0:
            return "No Log selected."
        
        logPath = convert_string(selection[0].data(Qt.UserRole).toString())
        if logPath == None:
            return "ERROR: path is None"
        if not os.path.exists(logPath):
            return "File not found: " + logPath
        
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
        self.updateMemberInformation()
        
    def sendMessageToMember(self, lineEdit):
        selectedMember = self.get_selected_log_member()
        if selectedMember != None:
            get_server().call(convert_string(lineEdit.text()),client=selectedMember)
        
    def updateMemberInformation(self):
        self.memberInformationTable.clear()
        
        if self.get_selected_log_member() == None:
            self.memberInformationTable.setColumnCount(0)
            self.memberInformationTable.setHeaderLabel("No member selected.")
            return

        get_server().lockMembers()
        memberInformation = None
        try:
            if self.get_selected_log_member() in get_server().get_member_info():
                memberInformation = copy.deepcopy(get_server().get_member_info()[self.get_selected_log_member()])
        finally:
            get_server().releaseMembers()
            
        if memberInformation == None:
            self.memberInformationTable.setColumnCount(0)
            self.memberInformationTable.setHeaderLabel("No member information available.")
            return
        
        self.memberInformationTable.setColumnCount(len(memberInformation))
        headers = sorted(memberInformation.keys())
        self.memberInformationTable.setHeaderLabels(QStringList(headers))
        item = QTreeWidgetItem(self.memberInformationTable)
        for col, header in enumerate(headers):
            item.setData(col, Qt.DisplayRole, QVariant(memberInformation[header]))
        for col in range(self.memberInformationTable.columnCount()):
            self.memberInformationTable.resizeColumnToContents(col)
        
    def create_members_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setSpacing(0)
        
        self.dropdown_members_dict = {}
        self.dropdown_members_model = QStandardItemModel()
        self.dropdown_members_model.appendRow(QStandardItem(""))
        self.dropdown_members = QComboBox(widget)
        self.dropdown_members.setModel(self.dropdown_members_model)
        
        self.update_button = QPushButton("Send Update Command", widget)

        topLayout = QHBoxLayout()
        topLayout.setSpacing(10)
        topLayout.addWidget(self.dropdown_members, 1)
        topLayout.addWidget(self.update_button)
        self.requestLogsButton = QPushButton("Request Logfiles", widget)
        topLayout.addWidget(self.requestLogsButton)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Member Information:", widget))
        self.memberInformationTable = QTreeWidget(widget)
        self.memberInformationTable.setMaximumHeight(65)
        self.memberInformationTable.setSelectionMode(QTreeWidget.NoSelection)
        layout.addWidget(self.memberInformationTable, 0)
                
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
        
        self.update_dropdown_members()
        self.memberSelectionChanged()
        self.log_tree_view.selectionModel().selectionChanged.connect(self.displaySelectedLogfile)
        self.dropdown_members.currentIndexChanged.connect(self.memberSelectionChanged)
        self.update_button.clicked.connect(self.request_update)
        self.requestLogsButton.clicked.connect(self.requestLogClicked)
        self.sendMessageButton.clicked.connect(partial(self.sendMessageToMember, messageInput))
        messageInput.returnPressed.connect(partial(self.sendMessageToMember, messageInput))
        
        return widget
    
    def create_widget(self, parent):
        nb = QTabWidget(parent)
        #nb.setTabPosition(QTabWidget.West)
        
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
    