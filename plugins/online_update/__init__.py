from lunchinator import get_server    
from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, log_error, log_info, get_settings
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
import urllib2,sys,os
    
class online_update(iface_gui_plugin):
    def __init__(self):
        super(online_update, self).__init__()
        self.options = [(("check_url", "update URL"), "http://lunchinator.de/files/setup_lunchinator.exe")]
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QStandardItemModel, QStandardItem, QWidget, QHBoxLayout, QLabel, QSizePolicy, QPushButton

        iface_gui_plugin.create_widget(self, parent)        
        
        self.widget = QWidget(parent)
        self.but = QPushButton("Check for Update", self.widget)
        self.but.clicked.connect(self.check_for_update)
        
        layout = QHBoxLayout(self.widget)
        layout.addWidget(self.but)
        
#         widget.setMaximumHeight(widget.sizeHint().height())
        self.widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        
    def installer_downloaded(self):
        log_info("updater successfully downloaded")
    
    def error_while_downloading(self):
        log_error("error while downloading update")
        
    def check_for_update(self):
        log_info("Checking for Update")
        self._installer_url = self.options["check_url"]
        self._local_installer_file = os.path.join(get_settings().get_main_config_dir(), "setup_lunchinator.exe")
        installer_download = DownloadThread(getValidQtParent(), self._installer_url, target = open(self._local_installer_file, "wb"))
        installer_download.success.connect(self.installer_downloaded)
        installer_download.error.connect(self.error_while_downloading)
        installer_download.finished.connect(installer_download.deleteLater)
        installer_download.start()