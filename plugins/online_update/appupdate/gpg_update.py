from online_update.appupdate.app_update_handler import AppUpdateHandler
from lunchinator.utilities import getGPGandKey, getValidQtParent
from lunchinator.download_thread import DownloadThread
from lunchinator import get_settings
from lunchinator.log.logging_func import loggingFunc
import os, contextlib, json

class GPGUpdateHandler(AppUpdateHandler):
    """Base class for updaters that download GPG signed packages and install them."""
    
    def __init__(self, logger, urlBase):
        AppUpdateHandler.__init__(self, logger)
        self._urlBase = urlBase
        self._version_info = {}
        self._local_installer_file = None
    
    def activate(self):
        AppUpdateHandler.activate(self)
        self._checkGPG()
        
    def _getInitialStatus(self):
        return "Not checked."
        
    def canCheckForUpdate(self):
        return True
        
    @loggingFunc
    def checkForUpdate(self):
        if not self._has_gpg():
            # user clicked on "Install GPG"
            return self._installGPG()
        
        self._setStatus("Checking %s for Update..."%self._urlBase)
        
        if self._getCheckURLBase() == None:
            self._setStatus("Auto Update does not work on your OS yet.", True)
            return
        
        url = self._getCheckURLBase() + "/latest_version.asc"
        version_download = DownloadThread(getValidQtParent(), self.logger, url)
        version_download.success.connect(self._versionInfoDownloaded)
        version_download.error.connect(self._errorDownloading)
        version_download.finished.connect(version_download.deleteLater)
        version_download.start()
        
    def prepareInstallation(self, commands):
        if os.path.isfile(self._local_installer_file):
            return self._prepareInstallation(self._local_installer_file, commands)
    
    def _has_gpg(self):
        gpg, _key = getGPGandKey(self.logger)
        return gpg != None
    
    def _checkGPG(self):
        # check for GPG
        if self._has_gpg():
            self.checkForUpdate()
        else:
            self._setStatus("GPG not installed or not working properly.")
        
    @loggingFunc    
    def _downloadProgressChanged(self, _t, prog):
        if self._ui != None:
            self._ui.setProgress(prog)
            
    def _updateVersionLabel(self):
        if self._version_info and self._ui != None:
            vstr = "Online Version Info:\n"
            for k, v in self._version_info.iteritems():
                vstr += str(k) + ":" + str(v) + "\n"
            self._ui.setAppStatusToolTip(vstr)
            
    def _verifySignature(self, signedString):
        gpg, _keyid = getGPGandKey(self.logger)
        if gpg == None:
            return None
        v = gpg.verify(str(signedString))
        if not v:
            self.logger.error("Verification of Signature failed")
            return False
        
        return v
    
    def _checkHash(self):
        if not os.path.isfile(self._local_installer_file):
            return False
        
        fileHash = ""
        try:
            import hashlib
            with contextlib.closing(open(self._local_installer_file, "rb")) as fileToHash:
                md = hashlib.md5()
                md.update(fileToHash.read())
                fileHash = md.hexdigest()
        except:
            self._setStatus("Could not calculate hash of installer", True)
            return False
            
        if fileHash != self._version_info["Installer Hash"]:
            self._setStatus("Installer Hash wrong %s!=%s" % (fileHash, self._version_info["Installer Hash"]), True)
            return False
            
        self._setStatus("New version %s downloaded, ready to install" % self._getDownloadedVersion())
        self._installReady()
            
        return True
    
    def _getDownloadedVersion(self):
        if self._version_info != None:
            return self._version_info[u"Version String"] if u"Version String" in self._version_info else self._version_info["Commit Count"]
        
    @loggingFunc
    def _versionInfoDownloaded(self, thread):
        try:
            signedString = thread.getResult()
        except:
            self._setStatus("Version info not available", True)
            return
        
        self.logger.debug("Update: Got version info, checking signature %s", signedString)
        
        ver_result = False
        try:
            ver_result = self._verifySignature(signedString)
        except:
            self.logger.exception("Error verifying signature")
            self._setStatus("Signature could not be verified because of unknown error", True)
            return
        
        if not ver_result:
            self._setStatus("Signature could not be verified", True)
            return
                
        self.logger.debug("Updater: Signature OK, checking version info")
        
        for l in signedString.splitlines():
            info = l.split(":", 1)
            if len(info) > 1:
                self._version_info[info[0]] = info[1].strip()
                
        if not self._version_info.has_key("URL") or not self._version_info.has_key("Commit Count"):
            self._setStatus("Version Info corrupt - URL and/or Commit Count missing", True)
            self.logger.debug(str(self._version_info))
            return
        else:
            try:
                self._version_info["Commit Count"] = int(self._version_info["Commit Count"])
            except:
                self._setStatus("Commit Count has wrong format: " % self._version_info["Commit Count"], True)
                return
                
        self._updateVersionLabel()
        
        self._installer_url = self._getCheckURLBase() + self._version_info["URL"]
        self._local_installer_file = os.path.join(get_settings().get_main_config_dir(), self._installer_url.rsplit('/', 1)[1])
        
        if self._hasNewVersion() and u"Change Log" in self._version_info:
            try:
                changeLog = json.loads(self._version_info[u"Change Log"])
                self._setChangeLog(changeLog)
            except:
                self.logger.exception("Error reading change log.")
                self._setChangeLog(["Error loading change log"])
        
        if self._hasNewVersion():
            # check if we already downloaded this version before
            if not self._checkHash():
                self._setStatus("New Version %s available, Downloading ..." % (self._getDownloadedVersion()), progress=True)
                
                installer_download = DownloadThread(getValidQtParent(), self.logger, self._installer_url, target=open(self._local_installer_file, "wb"), progress=True)
                installer_download.progressChanged.connect(self._downloadProgressChanged)
                installer_download.success.connect(self._installerDownloaded)
                installer_download.error.connect(self._errorDownloading)
                installer_download.finished.connect(installer_download.deleteLater)
                installer_download.start()
        else:
            self._setStatus("No new version available")
            
    @loggingFunc
    def _installerDownloaded(self, thread):
        try:
            # close the file object that keeps the downloaded data
            thread.getResult().close()
        except:
            self._setStatus("unexpected error after downloading installer", True)
            
        self._checkHash()
    
    @loggingFunc
    def _errorDownloading(self):
        self._setStatus("Download failed", True)
        
    def _hasNewVersion(self):
        return self._version_info and \
               self._version_info["Commit Count"] > int(get_settings().get_commit_count())
    
    ########### To be implemented in subclasses ###################
    def _prepareInstallation(self, _f, _commands):
        raise NotImplementedError()
    def _canInstallGPG(self):
        """If GPG is not available, this method determines if it can be automatically installed."""
        return False
    def _installGPG(self):
        """If _canInstallGPG() is True, this method is called when a GPG installation is requested."""
        raise NotImplementedError()
    def _getCheckURLBase(self):
        """Returns the base URL to check for updates."""
        return None
    