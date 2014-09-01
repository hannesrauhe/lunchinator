from lunchinator import get_settings, get_notification_center, HAS_GUI
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.callables import AsyncCall
from lunchinator.log.logging_func import loggingFunc

class RepoUpdateHandler(object):
    """Handles plugin repository updates."""
    
    def __init__(self, logger):
        self._ui = None
        self.logger = logger
        self._nOutdated = None
    
    def activate(self):
        get_notification_center().connectOutdatedRepositoriesChanged(self._processOutdated)
        if HAS_GUI:
            self.checkForUpdates()
    
    def deactivate(self):
        get_notification_center().disconnectOutdatedRepositoriesChanged(self._processOutdated)
    
    @loggingFunc
    def checkForUpdates(self):
        AsyncCall(getValidQtParent(),
                  self.logger,
                  get_settings().get_plugin_repositories().checkForUpdates)()
    
    def setUI(self, ui):
        self._ui = ui
        self._ui.checkForRepoUpdates.connect(self.checkForUpdates)
        self._updateRepoStatus(self._nOutdated)
        self._ui.setRepoUpdatesAvailable(self._nOutdated > 0)
        
    def _getRepoStatus(self, nOutdated=None):
        if nOutdated == None:
            nOutdated = get_settings().get_plugin_repositories().getNumOutdated()
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
    
    @loggingFunc
    def _processOutdated(self):
        nOutdated = get_settings().get_plugin_repositories().getNumOutdated()
        
        if nOutdated > 0:
            displayNotification("Update(s) available", self._getRepoStatus(), self.logger)
        if self._ui != None:
            self._ui.setRepoUpdatesAvailable(nOutdated > 0)
            self._updateRepoStatus(nOutdated)
        self._nOutdated = nOutdated
    
    def prepareInstallation(self, commands):
        toUpdate = get_settings().get_plugin_repositories().getOutdated()
        for path in toUpdate:
            commands.addGitPull(path)
