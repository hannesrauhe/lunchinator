from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QStandardItem, QStandardItemModel, QComboBox, QSplitter, QTextEdit, QTreeWidgetItem
from PyQt4.QtCore import Qt, QVariant, pyqtSlot, QTimer, QStringList, QThread
from lunchinator.history_line_edit import HistoryLineEdit
from functools import partial
from lunchinator import get_server, get_settings, convert_string, log_warning,\
    log_exception, log_debug, getLogLineTime, get_peers, get_notification_center
import os, sip, codecs, copy, shutil, contextlib, tarfile
from datetime import datetime
from lunchinator.lunch_datathread_qt import DataReceiverThread
from lunchinator.table_models import TableModelBase

class DropdownModel(TableModelBase):
    _NAME_KEY = u'name'
    _ID_KEY = u'ID'
    
    def __init__(self, dataSource):
        columns = [(u"Name", self._updateNameItem)]
        super(DropdownModel, self).__init__(dataSource, columns)
        
        # Called before server is running, no need to lock here
        for peerID in self.dataSource:
            infoDict = dataSource.getPeerInfo(pID=peerID)
            self.appendContentRow(peerID, infoDict)
            
    def _updateNameItem(self, _ip, infoDict, item):
        if infoDict == None:
            import traceback
            traceback.print_stack()
        peerID = infoDict[self._ID_KEY] if self._ID_KEY in infoDict else u""
        m_name = infoDict[self._NAME_KEY] if self._NAME_KEY in infoDict else u""
        
        if peerID == m_name:
            name = peerID
        else:
            name = "%s (%s)" % (m_name.strip(), peerID.strip())
        
        item.setText(name)

class MembersWidget(QWidget):
    def __init__(self, parent):
        super(MembersWidget, self).__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        self.dropdown_members_dict = {}
        self.dropdown_members_model = DropdownModel(get_peers())
        self.dropdown_members = QComboBox(self)
        self.dropdown_members.setModel(self.dropdown_members_model)
        
        self.update_button = QPushButton("Send Update Command", self)

        topLayout = QHBoxLayout()
        topLayout.setSpacing(10)
        topLayout.addWidget(self.dropdown_members, 1)
        topLayout.addWidget(self.update_button)
        self.requestLogsButton = QPushButton("Request Logfiles", self)
        topLayout.addWidget(self.requestLogsButton)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Member Information:", self))
        self.memberInformationTable = QTreeWidget(self)
        self.memberInformationTable.setMaximumHeight(65)
        self.memberInformationTable.setSelectionMode(QTreeWidget.NoSelection)
        layout.addWidget(self.memberInformationTable, 0)
                
        layout.addWidget(QLabel("Send Message:", self))
        
        sendMessageLayout = QHBoxLayout()
        sendMessageLayout.setSpacing(10)
        messageInput = HistoryLineEdit(self, "Enter a message")
        self.sendMessageButton = QPushButton("Send", self)
        sendMessageLayout.addWidget(messageInput, 1)
        sendMessageLayout.addWidget(self.sendMessageButton)
        layout.addLayout(sendMessageLayout)
        
        layout.addWidget(QLabel("Log files:", self))
        logSplitter = QSplitter(Qt.Horizontal, self)
        
        logListWidget = QWidget(self)
        logListLayout = QVBoxLayout(logListWidget)
        logListLayout.setContentsMargins(0, 0, 0, 0)
        
        self.log_tree_view = QTreeWidget(logSplitter)
        self.log_tree_view.setAlternatingRowColors(True)
        self.log_tree_view.setColumnCount(1)
        self.log_tree_view.setHeaderHidden(True)
        self.log_tree_view.setItemsExpandable(False)
        self.log_tree_view.setIndentation(0)
        
        logListLayout.addWidget(self.log_tree_view, 1)
        
        logListBottomLayout = QHBoxLayout()
        self.logSizeLabel = QLabel(logListWidget)
        logListBottomLayout.addWidget(self.logSizeLabel, 1)
        
        self.clearLogsButton = QPushButton("Clear", logListWidget)
        self.clearLogsButton.setEnabled(False)
        self.clearLogsButton.clicked.connect(self.clearLogs)
        logListBottomLayout.addWidget(self.clearLogsButton, 0)
        
        logListLayout.addLayout(logListBottomLayout)
        
        logSplitter.addWidget(logListWidget)
        
        self.log_area = QTextEdit(logListWidget)
        self.log_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_area.setReadOnly(True)
        logSplitter.addWidget(self.log_area)
        
        logSplitter.setStretchFactor(0, 0)
        logSplitter.setStretchFactor(1, 1)
        
        layout.addWidget(logSplitter, 1)
        
        self.memberSelectionChanged()
        self.log_tree_view.selectionModel().selectionChanged.connect(self.displaySelectedLogfile)
        self.dropdown_members.currentIndexChanged.connect(self.memberSelectionChanged)
        self.update_button.clicked.connect(self.request_update)
        self.requestLogsButton.clicked.connect(self.requestLogClicked)
        self.sendMessageButton.clicked.connect(partial(self.sendMessageToMember, messageInput))
        messageInput.returnPressed.connect(partial(self.sendMessageToMember, messageInput))
        
        get_notification_center().connectPeerAppended(self.dropdown_members_model.externalRowAppended)
        get_notification_center().connectPeerUpdated(self.dropdown_members_model.externalRowUpdated)
        get_notification_center().connectPeerRemoved(self.dropdown_members_model.externalRowRemoved)
        
    def destroy_widget(self):
        get_notification_center().disconnectPeerAppended(self.dropdown_members_model.externalRowAppended)
        get_notification_center().disconnectPeerUpdated(self.dropdown_members_model.externalRowUpdated)
        get_notification_center().disconnectPeerRemoved(self.dropdown_members_model.externalRowRemoved)
        
    def listLogfiles(self, basePath, sort = None):
        if sort is None:
            sort = lambda aFile : -self.getLogNumber(aFile)
        logList = [os.path.join(basePath, aFile) for aFile in os.listdir(basePath) if aFile.endswith(".log") and not os.path.isdir(os.path.join(basePath, aFile))]
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
                newName = os.path.join(os.path.dirname(aFile), "%d.log" % (logNum + shift))
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
                addedLogfiles.append((index + logOffset, os.path.join(basePath, os.path.basename(aLogFile))))
        shutil.rmtree(tmpPath, True)
        
        return numNew, addedLogfiles, renamedLogfiles
    
    def requestFinished(self):
        self.requestLogsButton.setEnabled(True)
        self.dropdown_members.setEnabled(True)
    
    @pyqtSlot(QThread, unicode)
    def cb_log_transfer_success(self, thread, path):
        path = convert_string(path)
        
        basePath = os.path.dirname(path)
        tmpPath = os.path.join(basePath, "tmp")
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
            
            shutil.move(path, os.path.join(tmpPath, "%d.log" % logNum))
            
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
        
        #TODO: how to check if visible?
#         if not self.visible:
#             return False
        
        if len(logsAdded) > 0 or len(logsRenamed) > 0:
            self.updateLogList(logsAdded, logsRenamed)
    
    @pyqtSlot(QThread)
    def cb_log_transfer_error(self, _thread):
        if not self.isVisible():
            return False
        self.log_area.setText("Error while getting log")
        self.requestFinished()
        
    def get_selected_log_member(self):
        member = str(self.dropdown_members.currentText())
        if not member:
            return None
        
        if "(" in member:
            # member contains name, extract ID
            member = member[member.rfind("(")+1:member.rfind(")")]
            
        return member
    
    def request_log(self, member = None, logNum = 0):
        if member is None:
            member = self.get_selected_log_member()
        if member != None:
            log_debug("Requesting log %d from %s" % (logNum, member))
            get_server().call("HELO_REQUEST_LOGFILE %s %d"%(DataReceiverThread.getOpenPort(category="log%s"%member), logNum), set([member]))
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
            get_server().call("HELO_UPDATE from GUI", set([member]))
    
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
             
    def formatFileSize(self, num):
        for x in ['Bytes','KB','MB','GB','TB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0
             
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
        text = text + "\n%s" % self.formatFileSize(os.path.getsize(logFile))
        if tooltip != None:
            item.setData(0, Qt.ToolTipRole, QVariant(tooltip)) 
        item.setData(0, Qt.UserRole, logFile)
        item.setData(0, Qt.DisplayRole, QVariant(text))
    
    @pyqtSlot()
    def clearLogs(self):
        for aLogFile in self.listLogFilesForMember(self.get_selected_log_member()):
            os.remove(aLogFile)
        self.updateLogList()
       
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
                self.logSizeLabel.setText("No logs")
                self.clearLogsButton.setEnabled(False)
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
        
        totalSize = 0
        for aLogFile in self.listLogFilesForMember(selectedMember):
            totalSize += os.path.getsize(aLogFile)
        
        self.logSizeLabel.setText("%s consumed" % self.formatFileSize(totalSize))
        self.clearLogsButton.setEnabled(True)
        #self.displaySelectedLogfile()
    
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
            get_server().call(convert_string(lineEdit.text()),set([selectedMember]))
            lineEdit.clear()
        
    def updateMemberInformation(self):
        self.memberInformationTable.clear()
        
        if self.get_selected_log_member() == None:
            self.memberInformationTable.setColumnCount(0)
            self.memberInformationTable.setHeaderLabel("No member selected.")
            return

        memberInformation = get_peers().getPeerInfo(pID=self.get_selected_log_member())
            
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