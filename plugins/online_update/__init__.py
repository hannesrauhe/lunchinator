from online_update.online_update_gui import OnlineUpdateGUI
from online_update.appupdate.git_update import GitUpdateHandler
from online_update.appupdate.mac_update import MacUpdateHandler
from online_update.appupdate.external_update import ExternalUpdateHandler
from online_update.appupdate.win_update import WinUpdateHandler
from online_update.appupdate.app_update_handler import AppUpdateHandler
from online_update.repoupdate.repo_update_handler import RepoUpdateHandler

from lunchinator import get_server, get_notification_center, get_settings
from lunchinator.lunch_settings import lunch_settings
from lunchinator.plugin import iface_general_plugin
from lunchinator.download_thread import DownloadThread
from lunchinator.shell_thread import ShellThread
from lunchinator.git import GitHandler
from lunchinator.utilities import getValidQtParent, displayNotification, \
    getGPG, getPlatform, PLATFORM_WINDOWS, PLATFORM_MAC, PLATFORM_LINUX, which,\
    getApplicationBundle, restartWithCommands
from lunchinator.commands import Commands
from lunchinator.log.logging_func import loggingFunc
    
import urllib2, sys, os, contextlib, subprocess, json, tempfile
from functools import partial
from xml.etree import ElementTree
    
class online_update(iface_general_plugin):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    
    def __init__(self):
        super(online_update, self).__init__()
        self.hidden_options = {"check_url": "http://update.lunchinator.de"}
        self._scheduleTimer = None
        self.force_activation = True
    
    def activate(self):
        from PyQt4.QtCore import QTimer
        iface_general_plugin.activate(self)
        
        if GitUpdateHandler.appliesToConfiguration():
            self._appUpdateHandler = GitUpdateHandler()
        elif MacUpdateHandler.appliesToConfiguration():
            self._appUpdateHandler = MacUpdateHandler(self.hidden_options["check_url"])
        elif ExternalUpdateHandler.appliesToConfiguration():
            self._appUpdateHandler = ExternalUpdateHandler()
        elif WinUpdateHandler.appliesToConfiguration():
            self._appUpdateHandler = WinUpdateHandler(self.hidden_options["check_url"])
        else:
            self._appUpdateHandler = AppUpdateHandler()
            
        self._repoUpdateHandler = RepoUpdateHandler()
            
        self._appUpdateHandler.activate()
        self._repoUpdateHandler.activate()
        
        get_notification_center().connectInstallUpdates(self.installUpdates)
        get_notification_center().connectRepositoriesChanged(self._repoUpdateHandler.checkForUpdates)
            
        if get_server().has_gui():
            self._scheduleTimer = QTimer(getValidQtParent())
            self._scheduleTimer.timeout.connect(self.checkForUpdate)
            self._scheduleTimer.start(online_update.CHECK_INTERVAL)
        
    def deactivate(self):
        if self._scheduleTimer != None:
            self._scheduleTimer.stop()
            self._scheduleTimer.deleteLater()
            
        get_notification_center().emitUpdatesDisabled()
        get_notification_center().disconnectInstallUpdates(self.installUpdates)
        get_notification_center().disconnectRepositoriesChanged(self._repoUpdateHandler.checkForUpdates)
        
        self._appUpdateHandler.deactivate()
        self._repoUpdateHandler.deactivate()
        iface_general_plugin.deactivate(self)
    
    def has_options_widget(self):
        return True
    
    def create_options_widget(self, parent):
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
        commands = Commands()
        
        if self._appUpdateHandler.isInstallReady():
            self._appUpdateHandler.prepareInstallation(commands)
            self._appUpdateHandler.executeInstallation(commands)
        if self._repoUpdateHandler.areUpdatesAvailable():
            self._repoUpdateHandler.prepareInstallation(commands)            
            restartWithCommands(commands)
        
if __name__ == '__main__':
    from lunchinator.plugin import iface_gui_plugin
    w = online_update()
    w.run_options_widget()
