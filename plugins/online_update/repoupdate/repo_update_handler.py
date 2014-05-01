from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator import get_settings, get_notification_center
from lunchinator.callables import AsyncCall

class RepoUpdateHandler(object):
    def __init__(self):
        self._ui = None
    
    def activate(self):
        get_notification_center().connectOutdatedRepositoriesChanged(self._processOutdated)
        self.checkForUpdates()
    
    def deactivate(self):
        get_notification_center().disconnectOutdatedRepositoriesChanged(self._processOutdated)
    
    def checkForUpdates(self):
        AsyncCall(getValidQtParent(),
                  get_settings().get_plugin_repositories().checkForUpdates)()
    
    def setUI(self, ui):
        self._ui = ui
        self._ui.checkForRepoUpdates.connect(self.checkForUpdates)
        self._updateRepoStatus()
        
    def _getRepoStatus(self, nOutdated=None):
        if nOutdated == None:
            with get_settings().get_plugin_repositories():
                nOutdated = len(get_settings().get_plugin_repositories().getOutdated())
        if nOutdated == 0:
            status = "There are no repositories that can be updated."
        elif nOutdated == 1:
            status = "1 plugin repository can be updated."
        else:
            status = "%d plugin repositories can be updated." % nOutdated
        return status
        
    def _updateRepoStatus(self, nOutdated=None):
        self._ui.setRepoStatus(self._getRepoStatus(nOutdated))
    
    def areUpdatesAvailable(self):
        return get_settings().get_plugin_repositories().areUpdatesAvailable()
    
    def _processOutdated(self):
        with get_settings().get_plugin_repositories():
            nOutdated = len(get_settings().get_plugin_repositories().getOutdated())
        
        if nOutdated > 0:
            displayNotification("Update(s) available", self._getRepoStatus())
        if self._ui:
            self._ui.setRepoUpdatesAvailable(nOutdated > 0)
            self._updateRepoStatus(nOutdated)
    
    def prepareInstallation(self, commands):
        toUpdate = get_settings().get_plugin_repositories().getOutdated()
        for path in toUpdate:
            commands.addGitPull(path)
