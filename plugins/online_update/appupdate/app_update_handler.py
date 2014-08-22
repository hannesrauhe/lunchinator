from lunchinator import get_settings, get_notification_center
from lunchinator.log import getLogger
from lunchinator.utilities import displayNotification, restartWithCommands

class AppUpdateHandler(object):
    """Abstract base class for Lunchinator application update handlers.
    
    Subclasses are used by the online_update plugin to handle the
    application update process.
    """
    
    def __init__(self):
        self._ui = None
        self._statusHolder = self._getInitialStatus()        
        self._progressHolder = False
        self._changelogHolder = None
        self._install_ready = False
    
    def isInstallReady(self):
        """Returns True if there is an update available and ready to install."""
        return self._install_ready
    
    def setUI(self, ui):
        """called from online_update.create_options_widget"""
        self._ui = ui
        
        if self._install_ready:
            self._ui.appInstallReady()
        
        self._ui.checkForAppUpdate.connect(self.checkForUpdate)
        
        self._ui.setAppStatus(self._statusHolder, self._progressHolder)
        if self._changelogHolder:
            self._ui.setAppChangeLog(self._changelogHolder)
    
    def getInstalledVersion(self):
        """Returns the version string to be displayed in the version label"""
        return get_settings().get_version()
    
    def _setChangeLog(self, log):
        """
        Caches or displays the given change log.
        log: list of strings
        """
        if self._ui != None:
            self._ui.setAppChangeLog(log)
        else:
            self._changelogHolder = log
    
    def _setStatus(self, status, err=False, progress=False):
        """Caches or displays a status message.
        
        status -- The message to be displayed
        err -- True if the message is an error
        progress -- True if the status incorporates progress information.
            The progress bar will be made visible based on this parameter.
        """
        if err:
            getLogger().error("Updater: %s", status)
            status = "Error: " + status
        else:
            getLogger().info("Updater: %s", status)
            
        if self._ui != None:
            self._ui.setAppStatus("Status: " + status, progress)
        else:
            self._statusHolder = "Status: " + status
            self._progressHolder = progress
        
    def _installReady(self):
        """Makes the install button enabled/disabled"""
        self._install_ready = True
        get_notification_center().emitApplicationUpdate()
        displayNotification("New Version Available", "Install via Update Plugin")
        if self._ui != None:
            self._ui.appInstallReady()    
            
    ############# To be implemented in subclass ##############
    
    def activate(self):
        """Called from online_update.activate"""
        pass
    
    def deactivate(self):
        """Called from online_update.deactivate"""
        pass
    
    def _getInitialStatus(self):
        """Returns the initial status message that is displayed as soon as the widget is created."""
        return u"Application updates are not available on your system."
    
    def canCheckForUpdate(self):
        """Returns True if this handler can check for updates."""
        return False
            
    def checkForUpdate(self):
        """Checks for updates.
        
        Called if canCheckForUpdate is True and either the user requested
        an update check or a scheduled update checking takes place.
        """
        pass
    
    def prepareInstallation(self, commands):
        """Prepares the installation process.
        
        commands -- a lunchinator.commands.Commands instance.
                    This method adds all the necessary commands
                    that should be executed to perform the update.
        """
        raise NotImplementedError()
    
    def executeInstallation(self, commands):
        """Usually means to install and restart"""
        
        restartWithCommands(commands)
    