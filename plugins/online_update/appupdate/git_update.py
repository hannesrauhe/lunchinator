from online_update.appupdate.app_update_handler import AppUpdateHandler
from lunchinator.git import GitHandler
from lunchinator.callables import AsyncCall
from lunchinator.utilities import getValidQtParent
from __builtin__ import True
from lunchinator import get_settings, log_info, log_error
import shutil
import os
import sys

class GitUpdateHandler(AppUpdateHandler):
    UPDATE_SCRIPT = get_settings().get_resource("bin", "updateViaGit.py")
    UPDATE_SCRIPT_EXEC_PATH = os.path.join(get_settings().get_main_config_dir(), "updateViaGit.py")

    @classmethod
    def appliesToConfiguration(cls):
        return GitHandler.hasGit()
    
    def activate(self):
        AppUpdateHandler.activate(self)
        self.checkForUpdate()
        
    def _getInitialStatus(self):
        return "Not checked."
        
    def getInstalledVersion(self):
        return get_settings().get_commit_count()
        
    def canCheckForUpdate(self):
        return True
        
    def checkForUpdate(self):
        self._setStatus("Checking for update...")
        AsyncCall(getValidQtParent(),
                  GitHandler.needsPull,
                  self._checkUpdateSuccess,
                  self._checkUpdateError)(returnReason=True)
        
    def _checkUpdateSuccess(self, tup):
        needsPull, reason = tup
        if needsPull:
            self._setStatus("Repository can be updated to version %s." % GitHandler.getRemoteCommitCount())
            self._installReady()
        else:
            self._setStatus(u"No update: " + reason)
            
    def _checkUpdateError(self, msg=None):
        st = u"Checking for update failed"
        if msg:
            st += u": " + msg
        self._setStatus(st, True)
        
    def prepareInstallation(self, commands):
        shutil.copy(self.UPDATE_SCRIPT, self.UPDATE_SCRIPT_EXEC_PATH)
        if os.path.isfile(self.UPDATE_SCRIPT_EXEC_PATH):
            commands.addGitPull(get_settings().get_main_package_path())
        else:
            log_error("Update Script was not found at %s" % self.UPDATE_SCRIPT_EXEC_PATH)
