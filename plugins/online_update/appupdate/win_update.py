from online_update.appupdate.gpg_update import GPGUpdateHandler
from lunchinator.utilities import PLATFORM_WINDOWS, getPlatform, stopWithCommands
from lunchinator import get_server
from lunchinator.log import getLogger
import os

class WinUpdateHandler(GPGUpdateHandler):
    @classmethod
    def appliesToConfiguration(cls):
        return get_server().has_gui() and getPlatform() == PLATFORM_WINDOWS
    
    def _getCheckURLBase(self):
        return self._urlBase + "/win/"
    
    def _prepareInstallation(self, localFile, commands):
        pass
    
    def executeInstallation(self, commands):
        """installer restarts the lunchinator"""
        if os.path.isfile(self._local_installer_file):        
            stopWithCommands([self._local_installer_file, "/SILENT"])
        else:
            getLogger().exception("Local Installer not found: %s", self._local_installer_file)
    
        