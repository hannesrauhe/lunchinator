from lunchinator import get_server
from lunchinator.lunch_settings import lunch_settings
from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, log_error, log_info, get_settings, log_debug
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
import urllib2,sys,os,contextlib, subprocess
    
class online_update(iface_gui_plugin):
    def __init__(self):
        super(online_update, self).__init__()
        self.options = [(("check_url", "update URL"), "http://update.lunchinator.de/")]
        self._avail_version = 0
        self._statusLabel = None
        self._versionLabel = None
        self._status_holder = "not checked"        
        self._version_info = {}
        self._local_installer_file = os.path.join(get_settings().get_main_config_dir(), "setup_lunchinator.exe")
        self._install_ready = False
        self._installButton = None
    
    def activate(self):
        iface_gui_plugin.activate(self)
        self.check_for_update()
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QStandardItemModel, QStandardItem, QWidget, QVBoxLayout, QLabel, QSizePolicy, QPushButton, QTextEdit

        iface_gui_plugin.create_widget(self, parent)        
        
        widget = QWidget(parent)        
        layout = QVBoxLayout(widget)
        
        versionLabel = QLabel("Installed Version: "+get_settings().get_commit_count())
        layout.addWidget(versionLabel)
        
        self._statusLabel = QLabel("Status: "+self._status_holder)
        layout.addWidget(self._statusLabel)
        
        checkButton = QPushButton("Check for Update", parent)
        checkButton.clicked.connect(self.check_for_update)
        layout.addWidget(checkButton)
        
        self._installButton = QPushButton("Install Update and Restart", parent)
        self._installButton.clicked.connect(self.install_update)
        self._installButton.setEnabled(self._install_ready)
        layout.addWidget(self._installButton)
        
        self._versionLabel = QTextEdit("")
        self._update_version_label()
        layout.addWidget(self._versionLabel)
        
        widget.setMaximumHeight(widget.sizeHint().height())
        widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)   
        return widget  
        
    def check_for_update(self):
        self._set_status("Checking for Update...")
        
        version_download = DownloadThread(getValidQtParent(), self.options["check_url"])
        version_download.success.connect(self.version_info_downloaded)
        version_download.error.connect(self.error_while_downloading)
        version_download.finished.connect(version_download.deleteLater)
        version_download.start()
        
    def install_update(self):
        if os.path.isfile(self._local_installer_file):
            self._set_status("Starting Installer")
            args = [self._local_installer_file, "/SILENT"]
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
            get_server().call("HELO_STOP installer_update",client="127.0.0.1")
    
    def _set_status(self,status,err=False):
        if err:
            log_exception("Updater: "+status)
            status="Error: "+status
        else:
            log_info("Updater: "+status)
        if self._statusLabel:
            self._statusLabel.setText("Status: "+status)
        else:
            self._status_holder = status
            
    def _update_version_label(self):
        if self._version_info and self._versionLabel:
            vstr = "Online Version Info:\n"
            for k,v in self._version_info.iteritems():
                vstr += str(k)+":"+str(v)+"\n"
            self._versionLabel.setText(vstr)       
            
    def _verify_signature(self,signedString):
        from gnupg.gnupg import GPG
        gbinary = os.path.join(get_settings().get_lunchdir(),"gnupg","gpg.exe")
        ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")
        pub_key = os.path.join(get_settings().get_lunchdir(),"lunchinator_pub_0x17F57DC2.asc")
        if not os.path.isfile(gbinary):
            log_error("GPG not found")
            return False
        if not os.path.isfile(pub_key):
            log_error("Public Key not found")
            return False
            
        gpg = GPG(gbinary,ghome)
        
        with contextlib.closing(open(pub_key,"r")) as pub_keyf:
            gpg.import_keys(pub_keyf.read())
            
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
            with contextlib.closing(open(self._local_installer_file,"rb")) as fileToHash:
                md = hashlib.md5()
                md.update(fileToHash.read())
                fileHash = md.hexdigest()
        except:
            self._set_status("Could not calculate hash of installer", True)
            return False
            
        if fileHash!=self._version_info["Installer Hash"]:
            self._set_status("Installer Hash wrong %s!=%s"%(fileHash, self._version_info["Installer Hash"]), True)
            return False
            
        self._set_status("installer successfully downloaded - ready to install_update")
        self._install_ready = True
        if self._installButton:
            self._installButton.setEnabled(self._install_ready)
        displayNotification("New Version Available","Install via Update Plugin")
            
        return True
        
        
    def version_info_downloaded(self,thread):
        try:
            signedString = thread.getResult()
        except:
            self._set_status("Version info not available", True)
            return
        
        log_debug("Update: Got version info, checking signature",signedString)
        
        ver_result = False
        try:
            ver_result = self._verify_signature(signedString)
        except:
            self._set_status("Signature could not be verified because of unknown error", True)
            return
        
        if not ver_result:
            return
                
        log_debug("Updater: Signature OK, checking version info")
        
        for l in signedString.splitlines():
            info = l.split(":",2)
            if len(info)>1:
                self._version_info[info[0]] = info[1].strip()
                
        if not self._version_info.has_key("URL") or not self._version_info.has_key("Commit Count"):
            self._set_status("Version Info corrupt - URL and/or Commit Count missing", True)
            log_debug(str(self._version_info))
            return
        else:
            try:
                self._version_info["Commit Count"] = int(self._version_info["Commit Count"])
            except:
                self._statusLabel("Commit Count has wrong format: "%self._version_info["Commit Count"], True)
                return
                
        self._update_version_label()
        
        self._installer_url = self.options["check_url"]+self._version_info["URL"]
            
        if self._version_info["Commit Count"]>int(get_settings().get_commit_count()):
            #check if we already downloaded this version before
            if not self._check_hash():
                self._set_status("New Version %d available, Downloading ..."%(self._version_info["Commit Count"]))
                installer_download = DownloadThread(getValidQtParent(), self._installer_url, target = open(self._local_installer_file, "wb"))
                installer_download.success.connect(self.installer_downloaded)
                installer_download.error.connect(self.error_while_downloading)
                installer_download.finished.connect(installer_download.deleteLater)
                installer_download.start()
        else:
            self._set_status("No new version available")
        
    def installer_downloaded(self,thread):
        try:
            #close the file object that keeps the downloaded data
            thread.getResult().close()
        except:
            self._set_status("unexpected error after downloading installer", True)
            
        self._check_hash()
    
    def error_while_downloading(self):
        self._set_status("Download failed",True)
        
        
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    w = online_update()
    iface_gui_plugin.run_standalone(lambda window : w.create_widget(window))
    