from online_update.appupdate.app_update_handler import AppUpdateHandler
from lunchinator import get_settings, get_server
from lunchinator.git import GitHandler
from lunchinator.callables import AsyncCall
from lunchinator.utilities import getValidQtParent
from lunchinator.log.logging_func import loggingFunc

class GitUpdateHandler(AppUpdateHandler):
    """Used if Lunchinator is run directly from git."""
    
    def __init__(self, logger):
        super(GitUpdateHandler, self).__init__(logger)
        self._gitHandler = GitHandler(logger)
        
    @classmethod
    def appliesToConfiguration(cls, logger):
        gh = GitHandler(logger)
        return gh.hasGit()
    
    def activate(self):
        AppUpdateHandler.activate(self)
        if self.canCheckForUpdate():
            self.checkForUpdate()
        
    def _getInitialStatus(self):
        return "Not checked."
        
    def getInstalledVersion(self):
        return get_settings().get_commit_count()
        
    def canCheckForUpdate(self):
        return get_server().has_gui()
    
    @loggingFunc
    def checkForUpdate(self):
        self._setStatus("Checking for update...")
        AsyncCall(getValidQtParent(),
                  self.logger,
                  self._gitHandler.needsPull,
                  self._checkUpdateSuccess,
                  self._checkUpdateError)(returnReason=True)
        
    @loggingFunc
    def _checkUpdateSuccess(self, tup):
        needsPull, reason = tup
        if needsPull:
            self._setStatus("Repository can be updated to version %s." % self._gitHandler.getRemoteCommitCount())
            self._installReady()
        else:
            self._setStatus(u"No update: " + reason)
            
    @loggingFunc
    def _checkUpdateError(self, msg=None):
        st = u"Checking for update failed"
        if msg:
            st += u": " + msg
        self._setStatus(st, True)
        
    def prepareInstallation(self, commands):
        commands.addGitPull(get_settings().get_main_package_path())