from lunchinator import get_server, log_warning
from lunchinator.lunch_settings import lunch_settings
from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import log_exception, log_error, log_info, get_settings, log_debug
from lunchinator.utilities import getValidQtParent, displayNotification, \
    getGPG, getPlatform, PLATFORM_WINDOWS, PLATFORM_MAC, PLATFORM_LINUX, which,\
    getApplicationBundle, stopWithCommand
from lunchinator.download_thread import DownloadThread
from lunchinator.shell_thread import ShellThread
import urllib2, sys, os, contextlib, subprocess, json
import tempfile
from functools import partial
from xml.etree import ElementTree
from online_update.gitUpdate import gitUpdate
    
class online_update(iface_general_plugin):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    
    def __init__(self):
        super(online_update, self).__init__()
        self.hidden_options = {"check_url": "http://update.lunchinator.de"}
        self._git_updater = None
        self._avail_version = 0
        self._statusLabel = None
        self._progressBar = None
        self._versionLabel = None
        self._status_holder = "not checked"        
        self._progress_holder = False
        self._version_info = {}
        self._local_installer_file = None
        self._install_ready = False
        self._installButton = None
        self._scheduleTimer = None
        self._changeLog = None
    
    def activate(self):
        from PyQt4.QtCore import QTimer
        iface_general_plugin.activate(self)
        if getPlatform() == PLATFORM_MAC:
            # check if /usr/local/bin is in PATH
            if "/usr/local/bin" not in os.environ["PATH"]:
                os.environ["PATH"] += ":/usr/local/bin"
        
        
        self._git_updater = gitUpdate()
        if self._git_updater.has_git():
            return
        
        self._git_updater = None
        
        if self._check_for_rpm_deb():
            self._set_status("Updates for the lunchinator are managed by your OS. "+
                             "You can deactivate the Auto Update plugin.")
            return
        
        # check for GPG
        if self._has_gpg():
            self.check_for_update()
        else:
            self._set_status("GPG not installed or not working properly.")
            
        self._scheduleTimer = QTimer(getValidQtParent())
        self._scheduleTimer.timeout.connect(self.check_for_update)
        self._scheduleTimer.start(online_update.CHECK_INTERVAL)
            
    def _check_for_rpm_deb(self):
        if getPlatform() != PLATFORM_LINUX:
            return False
         
        call = ["dpkg", "-s", "lunchinator"]         
        fh = open(os.path.devnull,"w")
        p = subprocess.Popen(call,stdout=fh, stderr=fh)
        retCode = p.returncode
        if retCode == 0:
            return True
                
        call = "rpm -qa | grep lunchinator"         
        fh = open(os.path.devnull,"w")
        p = subprocess.Popen(call,stdout=fh, stderr=fh, shell=True)
        retCode = p.returncode
        if retCode == 0:
            return True
        
        return False        
    
    def _has_gpg(self):
        gpg, _key = getGPG()
        return gpg != None
        
    def _can_install_gpg(self):
        return getPlatform() == PLATFORM_MAC    
    
    def deactivate(self):
        if self._scheduleTimer != None:
            self._scheduleTimer.stop()
            self._scheduleTimer.deleteLater()
        
        iface_general_plugin.deactivate(self)
    
    def create_options_widget(self, parent):
        if self._git_updater:
            return self._git_updater.create_options_widget(parent)
        
        from PyQt4.QtGui import QStandardItemModel, QStandardItem, QWidget, \
                                QVBoxLayout, QLabel, QSizePolicy, QPushButton, \
                                QTextEdit, QProgressBar, QStackedWidget
        from PyQt4.QtCore import Qt
       
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        # now add the new stuff
        versionLabel = QLabel("Installed Version: " + get_settings().get_commit_count())
        layout.addWidget(versionLabel, 0)
        
        self._statusLabel = QLabel("Status: " + self._status_holder)
        layout.addWidget(self._statusLabel, 0)
        
        self._progressBar = QProgressBar(parent)
        self._progressBar.setVisible(self._progress_holder)
        layout.addWidget(self._progressBar, 0)
        
        self._checkButton = QPushButton("Check for Update", parent)
        self._checkButton.clicked.connect(self.check_for_update)
        
        layout.addWidget(self._checkButton, 0)
        
        self._installButton = QPushButton("Install Update and Restart", parent)
        self._installButton.clicked.connect(self.install_update)
        self._installButton.setEnabled(self._install_ready)
        layout.addWidget(self._installButton, 0)
        
        self._bottomWidget = QStackedWidget(parent)
        self._bottomWidget.addWidget(QWidget(self._bottomWidget))
        self._changeLog = QTextEdit(self._bottomWidget)
        self._changeLog.setReadOnly(True)
        self._bottomWidget.addWidget(self._changeLog)
        layout.addWidget(self._bottomWidget, 1)
        
        widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        
        self._setInteractive(True)
        
        return widget  
        
    def _setChangelogVisible(self, v):
        self._bottomWidget.setCurrentIndex(1 if v else 0)
        
    def _downloadProgressChanged(self, _t, prog):
        if self._progressBar != None:
            self._progressBar.setValue(prog)
        
    def getCheckURLBase(self):
        if getPlatform() == PLATFORM_WINDOWS:
            return self.hidden_options["check_url"] + "/win/"
        elif getPlatform() == PLATFORM_MAC:
            return self.hidden_options["check_url"] + "/mac/"
        else:
            return None  # TODO
        
    def check_for_update(self):
        if not self._has_gpg():
            # user clicked on "Install GPG"
            return self.install_gpg()
        
        self._set_status("Checking for Update...")
        
        if self.getCheckURLBase() == None:
            self._set_status("Auto Update does not work on your OS yet.", True)
            return
        
        url = self.getCheckURLBase() + "/latest_version.asc"
        version_download = DownloadThread(getValidQtParent(), url)
        version_download.success.connect(self.version_info_downloaded)
        version_download.error.connect(self.error_while_downloading)
        version_download.finished.connect(version_download.deleteLater)
        version_download.start()
        
    def _setInteractive(self, i):
        if i:
            if not self._has_gpg():
                if self._can_install_gpg():
                    self._checkButton.setEnabled(True)
                    self._checkButton.setText("Install GPG")
                else:
                    self._checkButton.setEnabled(False)
            else:
                self._checkButton.setEnabled(True)
                self._checkButton.setText("Check for Update")
                    
            self._installButton.setEnabled(self._install_ready)
        else:
            self._checkButton.setEnabled(False)
            self._installButton.setEnabled(False)
        
    def install_gpg(self, phase=0, dt=None):
        if getPlatform() == PLATFORM_MAC:
            # TODO handle errors
            if phase == 0:
                self._setInteractive(False)
                
                self._set_status("Searching for latest version...")
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
                self._set_status("Downloading MacGPG...", progress=True)
                self._progressBar.setValue(0)
                
                dt = DownloadThread(getValidQtParent(), dmgURL, target=tmpFile, progress=True)
                dt.success.connect(partial(self._install_gpg_finished, 1))
                dt.error.connect(partial(self._install_gpg_failed, 1))
                dt.progressChanged.connect(self._downloadProgressChanged)
                dt.start()
                
            elif phase == 2:
                # indeterminate
                self._progressBar.setMaximum(0)
                self._set_status("Installing MacGPG...", progress=True)
                
                dmgFile = dt.target.name
                dt.close()
                
                st = ShellThread(getValidQtParent(), [get_settings().get_resource('bin', 'mac_gpg_installer.sh'), dmgFile], context=dmgFile, quiet=False)
                st.finished.connect(partial(self._install_gpg_finished, 2))
                st.start()
                
            elif phase == 3:
                dmgFile = dt.context
                if os.path.exists(dmgFile):
                    os.remove(dmgFile)
                
                self._progressBar.setMaximum(100)
                if dt.exitCode == 0:
                    self._set_status("MacGPG installed successfully.")
                else:
                    self._set_status("Error installing MacGPG.", err=True)
                    if dt.pErr:
                        log_error("Console output:", dt.pErr.strip())
                self._setInteractive(True)
        
    def _install_gpg_finished(self, phase, dt, _):
        self.install_gpg(phase + 1, dt)
        
    def _install_gpg_failed(self, phase, dt, _url):
        dt.close()
        if phase == 0:
            self._set_status("Error downloading MacGPG version information.", True)
        elif phase == 1:
            self._set_status("Error downloading MacGPG installer.", True)
            dmgFile = dt.target.name
            if os.path.exists(dmgFile):
                os.remove(dmgFile)
        
    def install_update(self):
        if os.path.isfile(self._local_installer_file):
            if getPlatform() == PLATFORM_WINDOWS:
                self._set_status("Starting Installer")
                stopWithCommand([self._local_installer_file, "/SILENT"])
            elif getPlatform() == PLATFORM_MAC:
                path = getApplicationBundle()
                if path == None:
                    self._set_status("Could not find application bundle. Cannot update.", True)
                else:
                    installer = get_settings().get_resource("bin", "mac_installer.sh")
                    stopWithCommand([installer, self._local_installer_file, path, str(os.getpid())])
        else:
            log_error("This platform does not support updates (yet).")
    
    def _set_status(self, status, err=False, progress=False):
        if self._progressBar != None:
            self._progressBar.setVisible(progress)
    
        if err:
            log_error("Updater: " + status)
            status = "Error: " + status
        else:
            log_info("Updater: " + status)
        if self._statusLabel:
            self._statusLabel.setText("Status: " + status)
        else:
            self._status_holder = status
            self._progress_holder = progress
            
    def _update_version_label(self):
        if self._version_info and self._statusLabel:
            vstr = "Online Version Info:\n"
            for k, v in self._version_info.iteritems():
                vstr += str(k) + ":" + str(v) + "\n"
            self._statusLabel.setToolTip(vstr)      
            
    def _verify_signature(self, signedString):
        gpg, _keyid = getGPG()
        if gpg == None:
            return None
        v = gpg.verify(str(signedString))
        if not v:
            log_error("Verification of Signature failed")
            return False
        
        return v
    
    def _check_hash(self):
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
            self._set_status("Could not calculate hash of installer", True)
            return False
            
        if fileHash != self._version_info["Installer Hash"]:
            self._set_status("Installer Hash wrong %s!=%s" % (fileHash, self._version_info["Installer Hash"]), True)
            return False
            
        self._set_status("New version %d downloaded, ready to install" % self._version_info["Commit Count"])
        self._install_ready = True
        if self._installButton:
            self._installButton.setEnabled(self._install_ready)
        displayNotification("New Version Available", "Install via Update Plugin")
            
        return True
        
        
    def version_info_downloaded(self, thread):
        try:
            signedString = thread.getResult()
        except:
            self._set_status("Version info not available", True)
            return
        
        log_debug("Update: Got version info, checking signature", signedString)
        
        ver_result = False
        try:
            ver_result = self._verify_signature(signedString)
        except:
            log_exception("Error verifying signature")
            self._set_status("Signature could not be verified because of unknown error", True)
            return
        
        if not ver_result:
            self._set_status("Signature could not be verified", True)
            return
                
        log_debug("Updater: Signature OK, checking version info")
        
        for l in signedString.splitlines():
            info = l.split(":", 2)
            if len(info) > 1:
                self._version_info[info[0]] = info[1].strip()
                
        if not self._version_info.has_key("URL") or not self._version_info.has_key("Commit Count"):
            self._set_status("Version Info corrupt - URL and/or Commit Count missing", True)
            log_debug(str(self._version_info))
            return
        else:
            try:
                self._version_info["Commit Count"] = int(self._version_info["Commit Count"])
            except:
                self._statusLabel("Commit Count has wrong format: " % self._version_info["Commit Count"], True)
                return
                
        self._update_version_label()
        
        self._installer_url = self.getCheckURLBase() + self._version_info["URL"]
        self._local_installer_file = os.path.join(get_settings().get_main_config_dir(), self._installer_url.rsplit('/', 1)[1])
        
        if u"Change Log" in self._version_info:
            from PyQt4.QtGui import QTextCursor, QTextListFormat
            self._changeLog.clear()
            document = self._changeLog.document()
            document.setIndentWidth(20)
            cursor = QTextCursor(document)
            
            cursor.insertText("Changes:\n")
        
            listFormat = QTextListFormat()
            listFormat.setStyle(QTextListFormat.ListDisc)
            cursor.insertList(listFormat)
        
            log = json.loads(self._version_info[u"Change Log"])
            cursor.insertText("\n".join(log))
            self._setChangelogVisible(True)
        
        if self._version_info["Commit Count"] > int(get_settings().get_commit_count()):
            get_server().controller.notifyUpdates()
            
            # check if we already downloaded this version before
            if not self._check_hash():
                self._set_status("New Version %d available, Downloading ..." % (self._version_info["Commit Count"]), progress=True)
                
                installer_download = DownloadThread(getValidQtParent(), self._installer_url, target=open(self._local_installer_file, "wb"), progress=True)
                installer_download.progressChanged.connect(self._downloadProgressChanged)
                installer_download.success.connect(self.installer_downloaded)
                installer_download.error.connect(self.error_while_downloading)
                installer_download.finished.connect(installer_download.deleteLater)
                installer_download.start()
        else:
            self._set_status("No new version available")
        
    def installer_downloaded(self, thread):
        try:
            # close the file object that keeps the downloaded data
            thread.getResult().close()
        except:
            self._set_status("unexpected error after downloading installer", True)
            
        self._check_hash()
    
    def error_while_downloading(self):
        self._set_status("Download failed", True)
        
        
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    w = online_update()
    w.run_options_widget()
