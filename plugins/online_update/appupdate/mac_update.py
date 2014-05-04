from online_update.appupdate.gpg_update import GPGUpdateHandler
import os
from functools import partial
from xml.etree import ElementTree
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent,\
    getApplicationBundle
from lunchinator.download_thread import DownloadThread
import tempfile
from lunchinator import log_debug, get_settings, log_error
from lunchinator.shell_thread import ShellThread

class MacUpdateHandler(GPGUpdateHandler):
    @classmethod
    def appliesToConfiguration(cls):
        return getPlatform() == PLATFORM_MAC and getApplicationBundle() != None
    
    def activate(self):
        GPGUpdateHandler.activate(self)
        
        # check if /usr/local/bin is in PATH
        if "/usr/local/bin" not in os.environ["PATH"]:
            os.environ["PATH"] += ":/usr/local/bin"
        
    def setUI(self, ui):
        GPGUpdateHandler.setUI(self, ui)
        self._updateCheckButtonText()
        
    def _updateCheckButtonText(self):
        self._ui.setCheckAppUpdateButtonText("Install GPG" if not self._has_gpg() else None)
        
    def _prepareInstallation(self, localFile, commands):
        path = getApplicationBundle()
        if path == None:
            self._setStatus("Could not find application bundle. Cannot update.", True)
        else:
            installer = get_settings().get_resource("bin", "mac_installer.sh")
            commands.addShellCommand([installer, localFile, path, str(os.getpid())])
        
    def _canInstallGPG(self):
        return True

    def _installGPG(self, phase=0, dt=None):
        if getPlatform() == PLATFORM_MAC:
            # TODO handle errors
            if phase == 0:
                self._ui.setInteractive(False)
                
                self._setStatus("Searching for latest version...")
                dt = DownloadThread(getValidQtParent(), "https://releases.gpgtools.org/nightlies/macgpg2/appcast.xml")
                dt.success.connect(partial(self._install_gpg_finished, 0))
                dt.error.connect(partial(self._install_gpg_failed, 0))
                dt.start()
                
            elif phase == 1:
                xmlContent = dt.getResult()
                dt.close()
                
                e = ElementTree.fromstring(xmlContent)
                dmgURL = e.iter("channel").next().iter("item").next().iter("enclosure").next().attrib["url"]
                
                tmpFile = tempfile.NamedTemporaryFile(suffix=".dmg", prefix="macgpg", delete=False)
                log_debug("Donloading", dmgURL, "to", tmpFile.name)
                self._setStatus("Downloading MacGPG...", progress=True)
                self._ui.setProgress(0)
                
                dt = DownloadThread(getValidQtParent(), dmgURL, target=tmpFile, progress=True)
                dt.success.connect(partial(self._install_gpg_finished, 1))
                dt.error.connect(partial(self._install_gpg_failed, 1))
                dt.progressChanged.connect(self._downloadProgressChanged)
                dt.start()
                
            elif phase == 2:
                # indeterminate
                self._ui.setProgressIndeterminate(True)
                self._setStatus("Installing MacGPG...", progress=True)
                
                dmgFile = dt.target.name
                dt.close()
                
                st = ShellThread(getValidQtParent(), [get_settings().get_resource('bin', 'mac_gpg_installer.sh'), dmgFile], context=dmgFile, quiet=False)
                st.finished.connect(partial(self._install_gpg_finished, 2))
                st.start()
                
            elif phase == 3:
                dmgFile = dt.context
                if os.path.exists(dmgFile):
                    os.remove(dmgFile)
                
                self._ui.setProgressIndeterminate(False)
                if dt.exitCode == 0:
                    self._setStatus("MacGPG installed successfully.")
                else:
                    self._setStatus("Error installing MacGPG.", err=True)
                    if dt.pErr:
                        log_error("Console output:", dt.pErr.strip())
                
                self._updateCheckButtonText()
                self._ui.setInteractive(True)
        
    def _install_gpg_finished(self, phase, dt, _):
        self.install_gpg(phase + 1, dt)
        
    def _install_gpg_failed(self, phase, dt, _url):
        dt.close()
        if phase == 0:
            self._setStatus("Error downloading MacGPG version information.", True)
        elif phase == 1:
            self._setStatus("Error downloading MacGPG installer.", True)
            dmgFile = dt.target.name
            if os.path.exists(dmgFile):
                os.remove(dmgFile)
    
    def _getCheckURLBase(self):
        return self._urlBase + "/mac/"
    
    