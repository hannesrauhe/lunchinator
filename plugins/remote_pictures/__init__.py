from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, log_error, convert_string,\
    log_warning, get_server, log_debug, get_peers
import urllib2,sys,tempfile,csv,contextlib,os,socket
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
from StringIO import StringIO
from functools import partial
from tempfile import NamedTemporaryFile
from urlparse import urlparse
    
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
    
    def deactivate(self):
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
        
    def downloadedPicture(self, category, description, thread, url):
        from PyQt4.QtGui import QPixmap, QImage
        name = "New Remote Picture"
        if category != None:
            name = name + " in category %s" % category
            
        # create temporary image file to display in notification
        url = convert_string(url)
        ext = os.path.splitext(urlparse(url).path)[1]
        newFile = NamedTemporaryFile(suffix=ext)
        newFile.write(thread.getResult())
        newFile.seek(0)
        displayNotification(name, description, newFile.name)
        
        self.gui.addPicture(newFile, url, category, description)
          
    def extract_pic(self,url,category,description):
        try:
            getValidQtParent()
        except:
            log_warning("Remote Pictures does not work without QT")
            return
        if not self.gui.hasPicture(url, category):
            downloadThread = DownloadThread(getValidQtParent(), url)
            downloadThread.success.connect(partial(self.downloadedPicture, category, description))
            downloadThread.error.connect(self.errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            log_debug("Remote Pics: Downloaded this url before, won't do it again:",url)
            
    def _generateIPList(self, listStr):
        for aPeer in listStr.split(";;"):
            aPeer = aPeer.strip()
            
            peerIDs = []
            if get_peers().isPeerID(pID=aPeer):
                # is a peer ID
                peerIDs = [aPeer]
            else:
                # check if it is a peer name
                peerIDs = get_peers().getPeerIDsByName(aPeer)
                if not peerIDs:
                    # might be hostname or IP
                    ip = socket.gethostbyname(aPeer)
                    if ip:
                        yield ip
                    
            for peerID in peerIDs:
                # yield each IP for this peer ID 
                for ip in get_peers().getPeerIPs(pID=peerID):
                    yield ip
            
    def generateTrustedIPs(self):
        return self._generateIPList(self.options['trusted_peers'])
                
    def generateUntrustedIPs(self):
        return self._generateIPList(self.options['untrusted_peers'])
            
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
            peerID = get_peers().getPeerID(pIP=ip)
            trustPolicy = self.options['trust_policy']
            reject = True
            if trustPolicy == u"Local":
                # TODO use ownID()
                if ip == u"127.0.0.1" or peerID == get_settings().get_ID():
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
                                      "%s wants to send you a picture. Do you want to accept pictures from this member?" % get_peers().getPeerName(pID=peerID),
                                      QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.NoToAll,
                                      self.gui)
                    box.setDefaultButton(QMessageBox.No)
                    box.button(QMessageBox.NoToAll).setText(u"No, Never")
                    box.button(QMessageBox.YesToAll).setText(u"Yes, Always")
                    res = box.exec_()
                    if res == QMessageBox.NoToAll:
                        self._appendListOption(u"untrusted_peers", peerID)
                    elif res == QMessageBox.YesToAll:
                        self._appendListOption(u"trusted_peers", peerID)
                        reject = False
                    elif res == QMessageBox.Yes:
                        reject = False
                    
            if reject:
                log_debug("Rejecting remote picture from %s (%s)" % (ip, peerID))
                return
            else:
                log_debug("Accepting remote picture from %s (%s)" % (ip, peerID))
            
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
