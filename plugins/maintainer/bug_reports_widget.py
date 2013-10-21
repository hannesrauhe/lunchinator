from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt4.QtCore import pyqtSlot, Qt, QVariant
from lunchinator import log_error, log_warning, log_debug
from lunchinator.table_models import TableModelBase
from lunchinator.login_dialog import LoginDialog
import json, httplib
from functools import partial
from maintainer.github import Github
from maintainer.callables import SyncCall, AsyncCall
        
class BugReportsWidget(QWidget):
    def __init__(self, parent, mt):
        super(BugReportsWidget, self).__init__(parent)
        self.mt = mt
        self.lunchinatorRepo = None
        self.github = None
        
        layout = QVBoxLayout(self)
        
        self.entry = QTextEdit(self)
        
        self.issues = {}
        self.issuesComboModel = IssuesComboModel()
        
        self.dropdown_reports = QComboBox(self)
        self.dropdown_reports.setModel(self.issuesComboModel)
        self.display_report()
        self.close_report_btn = QPushButton("Close Bug", self)
        self.close_report_btn.setEnabled(False)
        
        self.logInOutButton = QPushButton("Log in to GitHub", self)
        self.logInOutButton.setEnabled(False)
        
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
        
        self.logIn(force=False, updateReports=True)
            
    def tokenFetchSuccess(self, newToken):
        if newToken:
            self.mt.set_option(u"github_token", newToken, convert=False)
    
    def loginError(self):
        self.github = None
    
    def createTokenFromLogin(self, nextCall = None):
        # obtain a token
        loginDialog = LoginDialog(self, description="Please enter your GitHub login information. The login information is NOT stored as plain text.")
        loginDialog.setMinimumWidth(300)
        retValue = loginDialog.exec_()
        if retValue == LoginDialog.Accepted:
            log_debug("Logging into GitHub using username/password")
            self.github = Github(login_or_token=loginDialog.getUsername(), password=loginDialog.getPassword())
            successCall = SyncCall(self.tokenFetchSuccess, successCall=nextCall, errorCall=nextCall)
            errorCall = SyncCall(self.loginError, successCall=nextCall, errorCall=nextCall) 
            self.asyncGithubCall(self.fetchOAuthToken, successCall=successCall, errorCall=errorCall)

    def tokenLoginFailed(self, errorMessage, nextCall):
        self.github = None
        # token is probably wrong. Try to re-login with username/password
        QMessageBox.critical(self, "Error", errorMessage, buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
        errorMessage = None
        self.createTokenFromLogin(nextCall)

    def asyncGithubCall(self, call, successCall = None, errorCall = None):
        AsyncCall(self, call, successCall, errorCall).start()
        
    def logOut(self):
        # TODO is there a better way?
        self.github = None
        self.logInOutButton.setText("Log in to GitHub")
        
        updateReportsDropdown = SyncCall(self.updateReportsDropdown)    
        updateReports = AsyncCall(self, self.update_reports, successCall=updateReportsDropdown, errorCall=updateReportsDropdown)
        updateReports()
        
    @pyqtSlot()
    def logInOrOut(self):
        if self.github:
            self.logOut()
        else:
            self.logIn()
         
    def loginFinished(self, _, nextCall = None):
        """ called when the login process is finished, successful or not """
        self.logInOutButton.setEnabled(True)
        if not self.github:
            self.logInOutButton.setText("Log in to GitHub")
        else:
            self.logInOutButton.setText("Log off from GitHub")
        if nextCall != None:
            nextCall()

    def logIn(self, force=True, updateReports=False):
        self.logInOutButton.setEnabled(False)
        
        finalCall = self.loginFinished

        # always update reports on successful login
        updateReportsDropdown = SyncCall(self.updateReportsDropdown, successCall=finalCall, errorCall=finalCall)    
        finalSuccessCall = AsyncCall(self, self.update_reports, successCall=updateReportsDropdown, errorCall=updateReportsDropdown)
        if updateReports:
            finalErrorCall = finalSuccessCall
        else:
            finalErrorCall = finalCall  
        
        # initialize lunchinator repository before finishing
        finalCall = AsyncCall(self, self.initializeLunchinatorRepo, errorCall=finalErrorCall, successCall=finalSuccessCall)
        
        if self.mt.options[u"github_token"]:
            # log in with token
            log_debug("Logging into GitHub using OAuth Token")
            self.github = Github(login_or_token=self.mt.options[u"github_token"])
            if force:
                errorCall = partial(self.tokenLoginFailed, finalCall)
            else:
                errorCall = SyncCall(self.loginError, successCall=finalCall, errorCall=finalCall)
            self.asyncGithubCall(self.forceLogin, successCall=finalCall, errorCall=errorCall)
        elif force:
            # log in with username/password
            self.createTokenFromLogin(finalCall)  
        else:
            # cannot log in
            finalCall()  
            
    def selectedIssue(self):
        issueID = self.dropdown_reports.itemData(self.dropdown_reports.currentIndex(), IssuesComboModel.KEY_ROLE).toInt()[0]
        if not issueID in self.issues:
            log_error("ID of selected issue is not in issues dictionary")
            return None
        return self.issues[issueID]
        
    def display_report(self):
        if self.dropdown_reports.currentIndex()>=0:
            self.entry.setText(self.selectedIssue().body)
            
    def updateReportsDropdown(self, reports):
        newKeys = set()
        for issue in reports:
            newKeys.add(issue.number)
            self.issues[issue.number] = issue
            if not self.issuesComboModel.hasKey(issue.number):
                self.issuesComboModel.externalRowAppended(issue.number, issue)
            else:
                self.issuesComboModel.externalRowUpdated(issue.number, issue)
                
        oldKeys = set(self.issuesComboModel.keys)
        for removedKey in oldKeys - newKeys:
            log_debug("Removing issue %s", removedKey)
            self.issuesComboModel.externalRowRemoved(removedKey)
           
        self.close_report_btn.setEnabled(self.issuesComboModel.rowCount() > 0)   
    
    def closeReportFailed(self, message):
        QMessageBox.critical(self, "Error closing report", "Could not close report: %s" % message, buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
    
    def close_report(self):
        selectedIssue = self.selectedIssue()
        if selectedIssue == None:
            return
        if QMessageBox.question(self, "Confirmation", "Are you sure you want to close the issue \"%s\"?" % selectedIssue.title, buttons=QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.No) == QMessageBox.Yes:
            updateReports = AsyncCall(self, self.update_reports)
            displayError = SyncCall(self.closeReportFailed)
            closeReport = AsyncCall(self, self.async_closeReport, successCall=updateReports, errorCall=displayError)
            closeReport(selectedIssue)
            
    ################ ASYNCHRONOUS #####################
    
    def async_closeReport(self, issue):
        issue.edit(state='closed')
    
    def initializeLunchinatorRepo(self, _ = None):
        repoUser = self.mt.options[u"repo_user"]
        repoName = self.mt.options[u"repo_name"]
        if repoUser and repoName:
            if self.github:
                # initialize repo from my own account
                log_debug("Initializing Lunchinator repository %s/%s using GitHub user %s" % (repoUser, repoName, self.github.get_user().login))
                self.lunchinatorRepo = self.github.get_repo("%s/%s" % (repoUser, repoName))
            else:
                log_debug("Initializing Lunchinator repository %s/%s being logged off" % (repoUser, repoName))
                self.lunchinatorRepo = Github().get_user(repoUser).get_repo(repoName)
        else:
            log_warning("No Lunchinator GitHub repository specified.")
            
    def update_reports(self, _ = None):
        if self.lunchinatorRepo != None:
            log_debug("updating bug reports")
            return self.lunchinatorRepo.get_issues(state="open")
        else:
            log_warning("Cannot update bug reports, no repository")
            return []
            
    def fetchOAuthToken(self):
        return self.github.get_user().get_authorizations()[0].token

    def forceLogin(self):
        self.github.get_users()[0]


class IssuesComboModel(TableModelBase):
    def __init__(self):
        columns = [("Issue", self.updateIssueItem)]
        super(IssuesComboModel, self).__init__(None, columns)
        
    def updateIssueItem(self, _issueID, issue, item):
        item.setData(QVariant(issue.title), Qt.DisplayRole)
    