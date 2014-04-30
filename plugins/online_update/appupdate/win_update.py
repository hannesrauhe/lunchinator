from online_update.appupdate.gpg_update import GPGUpdateHandler
from lunchinator.utilities import PLATFORM_WINDOWS, getPlatform

class WinUpdateHandler(GPGUpdateHandler):
    @classmethod
    def appliesToConfiguration(cls):
        return getPlatform() == PLATFORM_WINDOWS
    
    def _getCheckURLBase(self):
        return self._urlBase + "/win/"
    
    def _prepareInstallation(self, localFile, commands):
        commands.addShellCommand([localFile, "/SILENT"])
        