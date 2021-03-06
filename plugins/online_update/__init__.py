from lunchinator import get_notification_center, lunchinator_has_gui
from lunchinator.plugin import iface_general_plugin
from lunchinator.utilities import getValidQtParent, restartWithCommands
from lunchinator.commands import Commands
from lunchinator.log.logging_func import loggingFunc
    
class online_update(iface_general_plugin):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    
    def __init__(self):
        super(online_update, self).__init__()
        self.hidden_options = {"check_url": "http://update.lunchinator.de"}
        self._scheduleTimer = None
        self.force_activation = True
        self._appUpdateHandler = None
        self._repoUpdateHandler = None
    
    def activate(self):
        iface_general_plugin.activate(self)
        
        try:
            from PyQt4.QtCore import QTimer
            from online_update.appupdate.git_update import GitUpdateHandler
            from online_update.appupdate.mac_update import MacUpdateHandler
            from online_update.appupdate.external_update import ExternalUpdateHandler
            from online_update.appupdate.win_update import WinUpdateHandler
            from online_update.appupdate.app_update_handler import AppUpdateHandler
            from online_update.repoupdate.repo_update_handler import RepoUpdateHandler
            self._activated = True
        except ImportError:
            self._activated = False
            self.logger.warning("ImportError, cannot activate Auto Update")
            return
        
        if GitUpdateHandler.appliesToConfiguration(self.logger):
            self._appUpdateHandler = GitUpdateHandler(self.logger)
        elif MacUpdateHandler.appliesToConfiguration(self.logger):
            self._appUpdateHandler = MacUpdateHandler(self.logger, self.hidden_options["check_url"])
        elif ExternalUpdateHandler.appliesToConfiguration(self.logger):
            self._appUpdateHandler = ExternalUpdateHandler(self.logger)
        elif WinUpdateHandler.appliesToConfiguration(self.logger):
            self._appUpdateHandler = WinUpdateHandler(self.logger, self.hidden_options["check_url"])
        else:
            self._appUpdateHandler = AppUpdateHandler(self.logger)
            
        self._repoUpdateHandler = RepoUpdateHandler(self.logger)
            
        self._appUpdateHandler.activate()
        self._repoUpdateHandler.activate()
        
        get_notification_center().connectInstallUpdates(self.installUpdates)
        get_notification_center().connectRepositoriesChanged(self._repoUpdateHandler.checkForUpdates)
            
        if lunchinator_has_gui():
            self._scheduleTimer = QTimer(getValidQtParent())
            self._scheduleTimer.timeout.connect(self.checkForUpdate)
            self._scheduleTimer.start(online_update.CHECK_INTERVAL)
        
    def deactivate(self):
        if self._activated:
            if self._scheduleTimer is not None:
                self._scheduleTimer.stop()
                self._scheduleTimer.deleteLater()
                
            get_notification_center().emitUpdatesDisabled()
            get_notification_center().disconnectInstallUpdates(self.installUpdates)
            get_notification_center().disconnectRepositoriesChanged(self._repoUpdateHandler.checkForUpdates)
            
            if self._appUpdateHandler is not None:
                self._appUpdateHandler.deactivate()
            if self._repoUpdateHandler is not None:
                self._repoUpdateHandler.deactivate()
        iface_general_plugin.deactivate(self)
    
    def has_options_widget(self):
        return True
    
    def create_options_widget(self, parent):
        from online_update.online_update_gui import OnlineUpdateGUI
        self._ui = OnlineUpdateGUI(self._appUpdateHandler.getInstalledVersion(), parent)
        self._ui.setCanCheckForAppUpdate(self._appUpdateHandler.canCheckForUpdate())
        self._ui.installUpdates.connect(self.installUpdates)
        
        self._appUpdateHandler.setUI(self._ui)
        self._repoUpdateHandler.setUI(self._ui)
        
        return self._ui
    
    def destroy_options_widget(self):
        self._ui.installUpdates.disconnect(self.installUpdates)
        iface_general_plugin.destroy_options_widget(self)
        
    @loggingFunc
    def checkForUpdate(self):
        if self._appUpdateHandler.canCheckForUpdate():
            self._appUpdateHandler.checkForUpdate()
        self._repoUpdateHandler.checkForUpdates()
        
    @loggingFunc
    def installUpdates(self):
        commands = Commands(self.logger)
        
        if self._appUpdateHandler.isInstallReady():
            self._appUpdateHandler.prepareInstallation(commands)
            self._appUpdateHandler.executeInstallation(commands)
        if self._repoUpdateHandler.areUpdatesAvailable():
            self._repoUpdateHandler.prepareInstallation(commands)            
            restartWithCommands(commands, self.logger)
        
if __name__ == '__main__':
    from lunchinator.plugin import iface_gui_plugin
    w = online_update()
    w.run_options_widget()
