from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt4.QtCore import pyqtSlot, QThread, Qt, QVariant, QSize
from lunchinator import log_error, log_debug, log_warning
from lunchinator.download_thread import DownloadThread
from lunchinator.table_models import TableModelBase
import json, webbrowser
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
    PREFERRED_WIDTH  = 400
    PREFERRED_HEIGHT = 150
    
    def __init__(self, parent, mt):
        super(BugReportsWidget, self).__init__(parent)
        self.mt = mt
        
        layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
        
        self.entry = QTextEdit(self)
        
        self.issues = {}
        self.issuesComboModel = IssuesComboModel()
        
        self.dropdown_reports = QComboBox(self)
        self.dropdown_reports.setModel(self.issuesComboModel)
        self.display_report()
        self.details_btn = QPushButton("Details", self)
        self.details_btn.setEnabled(False)
        self.refresh_btn = QPushButton("Refresh", self)
        create_report_btn = QPushButton("New", self)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_reports, 1)
        topLayout.addWidget(self.details_btn)
        topLayout.addWidget(self.refresh_btn)
        topLayout.addSpacing(20)
        topLayout.addWidget(create_report_btn)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Description:", self))
        
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        self.entry.setReadOnly(True)
        layout.addWidget(self.entry)
                
        self.dropdown_reports.currentIndexChanged.connect(self.display_report)
        self.details_btn.clicked.connect(self.displayReportDetails)
        self.refresh_btn.clicked.connect(self.update_reports)
        create_report_btn.clicked.connect(self.createBugReport)
        
        self.update_reports()

    def repoChanged(self):
        self.update_reports()

    def displayReportDetails(self):
        selectedIssue = self.selectedIssue()
        if selectedIssue == None:
            return
        url = selectedIssue.issueUrl
        if url != None:
            webbrowser.open(url, new=2)
            
    def isRepoSpecified(self):
        repoUser = self.mt.options[u"repo_user"]
        repoName = self.mt.options[u"repo_name"]
        if repoUser and repoName:
            return True
        return False

    @pyqtSlot(QThread, unicode)
    def downloadedIssues(self, thread, _):
        self.refresh_btn.setEnabled(self.isRepoSpecified())
        j = json.loads(thread.getResult())
        
        newKeys = set()
        for i, issueDict in enumerate(j):
            issue = Issue(issueDict)
            newKeys.add(issue.id)
            self.issues[issue.id] = issue
            if not self.issuesComboModel.hasKey(issue.id):
                self.issuesComboModel.externalRowInserted(issue.id, issue, i)
            else:
                self.issuesComboModel.externalRowUpdated(issue.id, issue)
        
        oldKeys = set(self.issuesComboModel.keys)
        for removedKey in oldKeys - newKeys:
            self.issuesComboModel.externalRowRemoved(removedKey)
        self.details_btn.setEnabled(self.issuesComboModel.rowCount() > 0)
        
    @pyqtSlot(QThread, unicode)
    def errorDownloadingIssues(self, _thread, _url):
        self.refresh_btn.setEnabled(self.isRepoSpecified())
        log_error("Error fetching issues from github.")

    def update_reports(self):
        self.refresh_btn.setEnabled(False)
        repoUser = self.mt.options[u"repo_user"]
        repoName = self.mt.options[u"repo_name"]
        if repoUser and repoName:
            log_debug("Fetching issues from repository %s/%s" % (repoUser, repoName))
            thread = DownloadThread(self, "https://api.github.com/repos/%s/%s/issues?state=open" % (repoUser, repoName))
            thread.finished.connect(thread.deleteLater)
            thread.error.connect(self.errorDownloadingIssues)
            thread.success.connect(self.downloadedIssues)
            thread.start()
        else:
            log_warning("No Lunchinator GitHub repository specified.")
            
    def createBugReport(self):
        repoUser = self.mt.options[u"repo_user"]
        repoName = self.mt.options[u"repo_name"]
        if repoUser and repoName:
            url = "https://github.com/%s/%s/issues/new" % (repoUser, repoName)
            if url != None:
                webbrowser.open(url, new=2)
        else:
            log_warning("No Lunchinator GitHub repository specified.")
            QMessageBox.critical(self, "No Repository", "No Lunchinator GitHub repository specified.", buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
        
    def selectedIssue(self):
        issueID = self.dropdown_reports.itemData(self.dropdown_reports.currentIndex(), IssuesComboModel.KEY_ROLE).toInt()[0]
        if not issueID in self.issues:
            log_error("ID of selected issue is not in issues dictionary")
            return None
        return self.issues[issueID]
        
    def display_report(self):
        if self.dropdown_reports.currentIndex()>=0:
            self.entry.setText(self.selectedIssue().description)    

    def sizeHint(self):
        return QSize(self.PREFERRED_WIDTH, self.PREFERRED_HEIGHT)

if __name__ == '__main__':
    import os
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
    iface_gui_plugin.run_standalone(lambda window : BugReportsWidget(window, maintainer_wrapper()))
            