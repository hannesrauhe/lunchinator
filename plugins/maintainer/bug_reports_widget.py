from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QMessageBox
from PyQt4.QtCore import pyqtSlot, QThread, Qt, QVariant, pyqtSignal
from lunchinator import log_error, log_warning, log_debug, log_exception
from lunchinator.table_models import TableModelBase
from lunchinator.login_dialog import LoginDialog
import json, httplib, inspect
from functools import partial
from maintainer.github import Github
from maintainer.github import GithubException
        
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
        AsyncCall.createCall(self, call, successCall, errorCall).start()
        
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
        
        if updateReports:
            finalCall = AsyncCall.createCall(self, self.update_reports, successCall=finalCall, errorCall=finalCall)
        
        # initialize lunchinator repository before finishing
        finalCall = AsyncCall.createCall(self, self.initializeLunchinatorRepo, errorCall=finalCall, successCall=finalCall)
        
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
        
    ################ ASYNCHRONOUS #####################
    
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
            reports = self.lunchinatorRepo.get_issues(state="open")
            for issue in reports:
                self.issues[issue.number] = issue
                if not self.issuesComboModel.hasKey(issue.number):
                    self.issuesComboModel.externalRowAppended(issue.number, issue)
                else:
                    self.issuesComboModel.externalRowUpdated(issue.number, issue)
        else:
            log_warning("Cannot update bug reports, no repository")
            
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
    
def getArgSpec(aCallable):
    if inspect.isfunction(aCallable):
        argSpec = inspect.getargspec(aCallable)
        numArgs = len(argSpec.args)
    elif inspect.ismethod(aCallable):
        argSpec = inspect.getargspec(aCallable)
        numArgs = len(argSpec.args) - 1
    else:
        argSpec = inspect.getargspec(aCallable.__call__)
        numArgs = len(argSpec.args) - 1
    return (argSpec, numArgs)
    
def takesOneArgument(aCallable):
    argSpec, numArgs = getArgSpec(aCallable)
    
    minArgs = numArgs
    if argSpec.defaults != None:
        minArgs -= len(argSpec.defaults)
    if minArgs > 1 or (numArgs < 1 and argSpec.varargs == None):
        return False
    return True

def assertTakesOneArgument(aCallable):
    if not takesOneArgument(aCallable):
        argSpec, _ = getArgSpec(aCallable)
        raise Exception("Not callable with exactly one argument: %s" % str(argSpec))  

class SyncCall(object):
    def __init__(self, call, successCall, errorCall):
        super(SyncCall, self).__init__()
        
        if successCall != None:
            if type(successCall) in (str, unicode):
                successCall = partial(log_warning, successCall)
        if errorCall != None:
            if type(errorCall) in (str, unicode):
                errorCall = partial(log_warning, errorCall)
                        
        assertTakesOneArgument(successCall)
        assertTakesOneArgument(errorCall)
        self._call = call
        self._success = successCall
        self._error = errorCall
        
    def __call__(self, prevResult = None):
        try:
            if takesOneArgument(self._call):
                result = self._call(prevResult)
            else:
                result = self._call()
                
            if self._success != None:
                self._success(result)
            return
        except GithubException as e:
            if u'message' in e.data:
                errorMessage = u"GitHub Error: %s" % (e.data[u'message'])
            else:
                errorMessage = u"GitHub Error: %s" % unicode(e)
            log_warning(errorMessage)
        except:
            errorMessage = u"Exception during asynchronous call"
            log_exception(errorMessage)
        if self._error != None:
            self._error(errorMessage)
        
class AsyncCall(QThread):
    success = pyqtSignal(object)
    error = pyqtSignal(unicode)
    
    @classmethod
    def createCall(cls, parent, callAsync, successCall = None, errorCall = None):
        assert callAsync != None
        call = cls(parent, callAsync)
        if successCall != None:
            if type(successCall) in (str, unicode):
                call.success.connect(partial(log_warning, successCall))
            else:
                call.success.connect(successCall)

        if errorCall != None:
            if type(errorCall) in (str, unicode):
                call.error.connect(partial(log_warning, errorCall))
            else:
                call.error.connect(errorCall)
        call.finished.connect(call.deleteLater)
        return call
    
    def __init__(self, parent, call):
        super(AsyncCall, self).__init__(parent)
        self._call = call

    def __call__(self, prevResult = None):
        self._prevResult = prevResult
        self.start()

    def run(self):
        try:
            if takesOneArgument(self._call):
                result = self._call(self._prevResult)
            else:
                result = self._call()
                
            self.success.emit(result)
            return
        except GithubException as e:
            if u'message' in e.data:
                errorMessage = u"GitHub Error: %s" % (e.data[u'message'])
            else:
                errorMessage = u"GitHub Error: %s" % unicode(e)
            log_warning(errorMessage)
        except:
            errorMessage = u"Exception during asynchronous call"
            log_exception(errorMessage)
        self.error.emit(errorMessage)
        