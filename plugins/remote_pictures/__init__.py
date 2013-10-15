from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, log_error, convert_string,\
    log_warning, get_server, log_debug
import urllib2,sys,tempfile
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
from cStringIO import StringIO
from IN import IP_ADD_MEMBERSHIP
    
class remote_pictures(iface_gui_plugin):
    def __init__(self):
        super(remote_pictures, self).__init__()
        self.options = [(("trust_policy", u"Accept remote pictures from", (u"Local", u"Everybody", u"Nobody", u"Selected Members")),u"Local"),
                        (("trusted_peers", u"Selected Members:"),u""),
                        (("smooth_scaling", u"Smooth scaling", self.smoothScalingChanged),False)]
        self.imageLabel = None
        self.imageTarget = None
        self.imageText = None
        self.last_url = "" 
        
    def smoothScalingChanged(self, _setting, newValue):
        self.imageLabel.smooth_scaling = newValue
    
    def activate(self):
        self.imageTarget = tempfile.NamedTemporaryFile()
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        self.imageTarget.close()
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from lunchinator.resizing_image_label import ResizingImageLabel
        from PyQt4.QtGui import QWidget, QVBoxLayout, QLabel
        from PyQt4.QtCore import QSize, Qt
        
        super(remote_pictures, self).create_widget(parent)
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        self.imageLabel = ResizingImageLabel(widget, True, QSize(400,400))
        layout.addWidget(self.imageLabel, 1)
        self.textLabel = QLabel(widget)
        self.textLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.textLabel, 0, Qt.AlignCenter)
        return widget

    def process_message(self,msg,addr,member_info):
        pass
    
    def errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % convert_string(url))
        thread.deleteLater()
        
    def downloadedPicture(self, _thread, _):
        from PyQt4.QtGui import QPixmap, QImage
        self.imageTarget.flush()
        displayNotification("New Remote Picture", self.imageText, self.imageTarget.name)
        image = QImage(self.imageTarget.name)
        self.imageLabel.setRawPixmap(QPixmap.fromImage(image))
        if self.imageText != None:
            self.textLabel.setText(self.imageText)
        else:
            self.textLabel.setText("")
          
    def extract_pic(self,url):
        try:
            getValidQtParent()
        except:
            log_warning("Remote Pictures does not work without QT")
            return
        if url!=self.last_url:
            self.last_url = url
            self.imageTarget.seek(0)
            self.imageTarget.truncate()
            downloadThread = DownloadThread(getValidQtParent(), url, self.imageTarget)
            downloadThread.success.connect(self.downloadedPicture)
            downloadThread.error.connect(self.errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            log_debug("Remote Pics: Downloaded this url before, won't do it again:",url)
            
    def generateTrustedIPs(self):
        for aPeer in self.options['trusted_peers'].split(";;"):
            ip = get_server().ipForMemberName(aPeer.strip())
            if ip != None:
                yield ip
            else:
                yield aPeer.strip()
            
    def process_event(self,cmd,value,ip,_info):
        if cmd=="HELO_REMOTE_PIC":
            trustPolicy = self.options['trust_policy']
            reject = True
            if trustPolicy == u"Local":
                if ip == "127.0.0.1" or ip == get_server().own_ip:
                    reject = False
            elif trustPolicy == "Everybody":
                reject = False
            elif trustPolicy == "Selected Members":
                if ip in (self.generateTrustedIPs()):
                    reject = False
                    
            if reject:
                log_debug("Rejecting remote picture from %s (%s)" % (ip, get_server().memberName(ip)))
                return
            else:
                log_debug("Accepting remote picture from %s (%s)" % (ip, get_server().memberName(ip)))
            
            url = value.split()[0]
            self.imageText = value[len(url):].strip()
                   
            self.extract_pic(url)
