from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, log_error, convert_string,\
    log_warning, get_server, log_debug
import urllib2,sys,tempfile,csv,contextlib
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
from StringIO import StringIO
from functools import partial
    
class remote_pictures(iface_gui_plugin):
    def __init__(self):
        super(remote_pictures, self).__init__()
        self.options = [((u"trust_policy", u"Accept remote pictures from", (u"Local", u"Everybody", u"Nobody", u"Selected Members")),u"Selected Members"),
                        ((u"ask_trust", u"Ask if an unknown member wants to send a picture"), True),
                        ((u"trusted_peers", u"Selected Members:"),u""),
                        ((u"untrusted_peers", u"Always reject pictures from:"),u""),
                        ((u"min_opacity", u"Minimum opacity of controls:", self.minOpacityChanged),20),
                        ((u"max_opacity", u"Maximum opacity of controls:", self.maxOpacityChanged),80),
                        ((u"thumbnail_size", u"Thumbnail Size:", self.thumbnailSizeChanged),150),
                        ((u"smooth_scaling", u"Smooth scaling", self.smoothScalingChanged),False)]
        self.gui = None
        self.imageTarget = None
        
    def _handleOpacity(self, newValue, signal):
        if newValue < 0:
            newValue = 0
        elif newValue > 100:
            newValue = 100
            
        signal.emit(float(newValue) / 100.)
        return newValue
        
    def minOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, self.gui.minOpacityChanged)
    
    def maxOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, self.gui.maxOpacityChanged)
    
    def thumbnailSizeChanged(self, _setting, newValue):
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        if newValue < RemotePicturesGui.MIN_THUMBNAIL_SIZE:
            newValue = RemotePicturesGui.MIN_THUMBNAIL_SIZE
        elif newValue > RemotePicturesGui.MAX_THUMBNAIL_SIZE:
            newValue = RemotePicturesGui.MAX_THUMBNAIL_SIZE
        
        self.gui.thumbnailSizeChanged(newValue)
        return newValue
        
    def smoothScalingChanged(self, _setting, newValue):
        self.gui.imageLabel.smooth_scaling = newValue
    
    def activate(self):
        iface_gui_plugin.activate(self)
        self.imageTarget = tempfile.NamedTemporaryFile()
        
    def deactivate(self):
        self.imageTarget.close()
        if self.visible:
            self.destroy_widget()
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        super(remote_pictures, self).create_widget(parent)
        self.gui = RemotePicturesGui(parent, self)
        return self.gui
    
    def destroy_widget(self):
        if self.gui != None:
            self.gui.destroyWidget()
        iface_gui_plugin.destroy_widget(self)

    def process_message(self,msg,addr,member_info):
        pass
    
    def errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % convert_string(url))
        thread.deleteLater()
        
    def downloadedPicture(self, category, description, _thread, url):
        from PyQt4.QtGui import QPixmap, QImage
        self.imageTarget.flush()
        name = "New Remote Picture"
        if category != None:
            name = name + " in category %s" % category
        displayNotification(name, description, self.imageTarget.name)
        
        self.gui.addPicture(self.imageTarget.name, convert_string(url), category, description)
          
    def extract_pic(self,url,category,description):
        try:
            getValidQtParent()
        except:
            log_warning("Remote Pictures does not work without QT")
            return
        if not self.gui.hasPicture(url, category):
            self.last_url = url
            self.imageTarget.seek(0)
            self.imageTarget.truncate()
            downloadThread = DownloadThread(getValidQtParent(), url, self.imageTarget)
            downloadThread.success.connect(partial(self.downloadedPicture, category, description))
            downloadThread.error.connect(self.errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            log_debug("Remote Pics: Downloaded this url before, won't do it again:",url)
            
    def _generatePeerList(self, listStr):
        for aPeer in listStr.split(";;"):
            ip = get_server().ipForMemberName(aPeer.strip())
            if ip != None:
                yield ip
            else:
                yield aPeer.strip()
            
    def generateTrustedIPs(self):
        return self._generatePeerList(self.options['trusted_peers'])
                
    def generateUntrustedIPs(self):
        return self._generatePeerList(self.options['untrusted_peers'])
            
    def _appendListOption(self, o, new_v):
        old_val = self.options[o]
        if len(old_val) > 0:
            val_list = old_val.split(";;")
        else:
            val_list = []
        val_list.append(new_v)
        new_val = ";;".join(val_list)
        self.set_option(o, new_val, convert=False)
            
    def process_event(self,cmd,value,ip,_info):
        if cmd=="HELO_REMOTE_PIC":
            trustPolicy = self.options['trust_policy']
            reject = True
            if trustPolicy == u"Local":
                if ip == u"127.0.0.1" or ip == get_server().own_ip:
                    reject = False
            elif trustPolicy == "Everybody":
                reject = False
            elif trustPolicy == "Selected Members":
                if ip in self.generateTrustedIPs():
                    reject = False
                elif self.gui != None and self.options[u"ask_trust"] and ip not in self.generateUntrustedIPs():
                    from PyQt4.QtGui import QMessageBox
                    box = QMessageBox(QMessageBox.Question,
                                      "Accept Picture",
                                      "%s wants to send you a picture. Do you want to accept pictures from this member?" % get_server().memberName(ip),
                                      QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.NoToAll,
                                      self.gui)
                    box.setDefaultButton(QMessageBox.No)
                    box.button(QMessageBox.NoToAll).setText(u"No, Never")
                    box.button(QMessageBox.YesToAll).setText(u"Yes, Always")
                    res = box.exec_()
                    if res == QMessageBox.NoToAll:
                        self._appendListOption(u"untrusted_peers", ip)
                    elif res == QMessageBox.YesToAll:
                        self._appendListOption(u"trusted_peers", ip)
                        reject = False
                    elif res == QMessageBox.Yes:
                        reject = False
                    
            if reject:
                log_debug("Rejecting remote picture from %s (%s)" % (ip, get_server().memberName(ip)))
                return
            else:
                log_debug("Accepting remote picture from %s (%s)" % (ip, get_server().memberName(ip)))
            
            with contextlib.closing(StringIO(value.encode('utf-8'))) as strIn:
                reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
                valueList = [aValue.decode('utf-8') for aValue in reader.next()]
                url = valueList[0]
                desc = None
                cat = None
                if len(valueList) > 1:
                    desc = valueList[1]
                if len(valueList) > 2:
                    cat = valueList[2]
            
            self.extract_pic(url, cat, desc)
