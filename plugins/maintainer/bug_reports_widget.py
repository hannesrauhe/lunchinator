from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit
from PyQt4.QtCore import pyqtSlot, QThread, Qt, QVariant
from lunchinator import log_error
from lunchinator.download_thread import DownloadThread
from lunchinator.table_models import TableModelBase
import json
from datetime import datetime

class Issue(object):
    Open = 1
    Closed = 2
    ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    
    def __init__(self, jsonDict):
        self.id = jsonDict[u"number"]
        self.title = jsonDict[u"title"]
        self.description = jsonDict[u"body"]
        self.issueUrl = jsonDict[u"html_url"]
        self.closeDate = None
        if jsonDict[u"state"] == u"closed":
            self.state = self.Closed
            self.closeDate = datetime.strptime(jsonDict[u"closed_at"], self.ISO_8601_FORMAT)
        else:
            self.state = self.Open
        self.creationDate = datetime.strptime(jsonDict[u"created_at"], self.ISO_8601_FORMAT)
        self.updateDate = datetime.strptime(jsonDict[u"updated_at"], self.ISO_8601_FORMAT)
        self.comments = jsonDict[u"comments"]
        self.commentsUrl = jsonDict[u"comments_url"]

class IssuesComboModel(TableModelBase):
    def __init__(self):
        columns = [("Issue", self.updateIssueItem)]
        super(IssuesComboModel, self).__init__(None, columns)
        
    def updateIssueItem(self, _issueID, issue, item):
        item.setData(QVariant(issue.title), Qt.DisplayRole)
        
class BugReportsWidget(QWidget):
    def __init__(self, parent, mt):
        super(BugReportsWidget, self).__init__(parent)
        self.mt = mt
        
        layout = QVBoxLayout(self)
        
        self.entry = QTextEdit(self)
        
        self.issues = {}
        self.issuesComboModel = IssuesComboModel()
        
        self.update_reports()
        self.dropdown_reports = QComboBox(self)
        self.dropdown_reports.setModel(self.issuesComboModel)
        self.display_report()
        self.close_report_btn = QPushButton("Close Bug", self)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_reports)
        topLayout.addWidget(self.close_report_btn)
        topLayout.addWidget(QWidget(self), 1)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Description:", self))
        
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        self.entry.setReadOnly(True)
        layout.addWidget(self.entry)
                
        self.dropdown_reports.currentIndexChanged.connect(self.display_report)
        self.close_report_btn.clicked.connect(self.close_report)

    @pyqtSlot(QThread, unicode)
    def downloadedIssues(self, thread, _):
        j = json.loads(thread.getResult())
        
        for issueDict in j:
            issue = Issue(issueDict)
            self.issues[issue.id] = issue
            if not self.issuesComboModel.hasKey(issue.id):
                self.issuesComboModel.externalRowAppended(issue.id, issue)
            else:
                self.issuesComboModel.externalRowUpdated(issue.id, issue)
        
    @pyqtSlot(QThread, unicode)
    def errorDownloadingIssues(self, _thread, _url):
        log_error("Error fetching issues from github.")

    def update_reports(self):
        thread = DownloadThread(self, "https://api.github.com/repos/hannesrauhe/lunchinator/issues?state=open")
        thread.finished.connect(thread.deleteLater)
        thread.error.connect(self.errorDownloadingIssues)
        thread.success.connect(self.downloadedIssues)
        thread.start()
        
    def selectedIssue(self):
        issueID = self.dropdown_reports.itemData(self.dropdown_reports.currentIndex(), IssuesComboModel.KEY_ROLE).toInt()[0]
        if not issueID in self.issues:
            log_error("ID of selected issue is not in issues dictionary")
            return None
        return self.issues[issueID]
        
    def display_report(self):
        if self.dropdown_reports.currentIndex()>=0:
            self.entry.setText(self.selectedIssue().description)
            
    def close_report(self):
        issue = self.selectedIssue()
        # TODO implement

