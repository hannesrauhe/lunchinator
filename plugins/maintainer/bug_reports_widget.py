from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt4.QtCore import pyqtSlot, QThread, Qt, QVariant
from lunchinator import log_error, log_warning, log_debug, log_exception
from lunchinator.download_thread import DownloadThread
from lunchinator.table_models import TableModelBase
from lunchinator.login_dialog import LoginDialog
import json, httplib, urllib
from datetime import datetime
from maintainer.github import Github
from maintainer.github import GithubException
        
class BugReportsWidget(QWidget):
    def __init__(self, parent, mt):
        super(BugReportsWidget, self).__init__(parent)
        self.mt = mt
        self.github = None
        
        layout = QVBoxLayout(self)
        
        self.entry = QTextEdit(self)
        
        self.issues = {}
        self.issuesComboModel = IssuesComboModel()
        
        self.update_reports()
        self.dropdown_reports = QComboBox(self)
        self.dropdown_reports.setModel(self.issuesComboModel)
        self.display_report()
        self.close_report_btn = QPushButton("Close Bug", self)
        
        self.logInOutButton = QPushButton("Log in to GitHub", self)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_reports)
        topLayout.addWidget(self.close_report_btn)
        topLayout.addWidget(QWidget(self), 1)
        topLayout.addWidget(self.logInOutButton)
        
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Description:", self))
        
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        self.entry.setReadOnly(True)
        layout.addWidget(self.entry)
                
        self.dropdown_reports.currentIndexChanged.connect(self.display_report)
        self.close_report_btn.clicked.connect(self.close_report)
        self.logInOutButton.clicked.connect(self.logInOrOut)
        
        self.logIn(force=False)

    def createTokenFromLogin(self):
        # obtain a token
        loginDialog = LoginDialog(self)
        retValue = loginDialog.exec_()
        if retValue == LoginDialog.Accepted:
            log_debug("Logging into GitHub using username/password")
            self.github = Github(login_or_token=loginDialog.getUsername(), password=loginDialog.getPassword())
            newToken = self.github.get_user().get_authorization(0).token
            if newToken:
                self.mt.set_option(u"github_token", newToken, convert=False)
            self.logInOutButton.setText("Log off from GitHub")

    def logIn(self, force=True):
        errorMessage = None
        try:
            if self.mt.options[u"github_token"]:
                try:
                    # try to login using OAuth token
                    log_debug("Logging into GitHub using OAuth Token")
                    self.github = Github(login_or_token=self.mt.options[u"github_token"])
                    # ensure login is performed
                    self.github.get_users()[0]
                    self.logInOutButton.setText("Log off from GitHub")
                    return True
                except GithubException as e:
                    if force:
                        # token is probably wrong. Try to re-login with username/password
                        if u'message' in e.data:
                            errorMessage = "Could not log in to GitHub using OAuth token: %s" % (e.data[u'message'])
                        else:
                            errorMessage = "Could not log in to GitHub using OAuth token: %s" % unicode(e)
                        log_warning(errorMessage)
                        QMessageBox.critical(self, "Error", errorMessage, buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
                        errorMessage = None
                        self.createTokenFromLogin()
                        return True
                    else:
                        # we don*t have to login.
                        raise
            elif force:
                self.createTokenFromLogin()
            return True
        except GithubException as e:
            if u'message' in e.data:
                errorMessage = "Could not log in to GitHub: %s" % (e.data[u'message'])
            else:
                errorMessage = "Could not log in to GitHub: %s" % unicode(e)
            self.github = None
            self.logInOutButton.setText("Log in to GitHub")
            log_warning(errorMessage)
        except:
            errorMessage = "Exception during login to GitHub"
            log_exception("Exception during login to GitHub")
            self.github = None
            self.logInOutButton.setText("Log in to GitHub")
            
        if force and errorMessage != None:
            QMessageBox.critical(self, "Error", errorMessage, buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
        return False
    
    def logOut(self):
        # TODO is there a better way?
        self.github = None
        self.logInOutButton.setText("Log in to GitHub")
        
    @pyqtSlot()
    def logInOrOut(self):
        if self.github:
            self.logOut()
        else:
            self.logIn()

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
        #params = urllib.urlencode({'@number': 12524, '@type': 'issue', '@action': 'show'})
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        conn = httplib.HTTPConnection("api.github.com")
        body = json.dumps({u"title":u"TestIssue",
                           u"body":u"Test Body"})
        conn.request("POST", "", body, headers)
        response = conn.getresponse()
        print response.status, response.reason
        
        data = response.read()
        print data
        
        conn.close()
        issue = self.selectedIssue()
        # TODO implement


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