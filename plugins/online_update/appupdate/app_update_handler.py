from lunchinator import log_error, log_info, get_settings

class AppUpdateHandler(object):
    def __init__(self):
        self._ui = None
        self._statusHolder = self._getInitialStatus()        
        self._progressHolder = False
        self._changelogHolder = None
        self._install_ready = False
    
    def activate(self):
        """Called from online_update.activate"""
        pass
    
    def deactivate(self):
        """Called from online_update.deactivate"""
        pass
    
    def isInstallReady(self):
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
            
    ############# To be implemented in subclass ##############
    
    def _getInitialStatus(self):
        return u"Application updates are not available on your system."
    
    def canCheckForUpdate(self):
        """Checks if update checks are possible"""
        return False
            
    def checkForUpdate(self):
        """Triggered from the check button"""
        pass
    
    def prepareInstallation(self):
        """
        Prepares the installation and returns a command to execute when restarting.
        The command is a list of arguments, as passed to subprocess.Popen.
        """
        raise NotImplementedError()
    
    def _setChangeLog(self, log):
        """
        Caches or displays the given change log.
        log: list of strings
        """
        if self._ui:
            self._ui.setAppChangeLog(log)
        else:
            self._changelogHolder = log
    
    def _setStatus(self, status, err=False, progress=False):
        """
        Caches or displays a status message.
        status: The message to be displayed
        err: True if it is an error
        progress: True if the status incorporates progress information.
            The progress bar will be made visible based on this parameter.
        """
        if err:
            log_error("Updater: " + status)
            status = "Error: " + status
        else:
            log_info("Updater: " + status)
            
        if self._ui:
            self._ui.setAppStatus("Status: " + status, progress)
        else:
            self._statusHolder = "Status: " + status
            self._progressHolder = progress
        
    def _installReady(self):
        """Makes the install button enabled/disabled"""
        self._install_ready = True
        if self._ui:
            self._ui.appInstallReady()    