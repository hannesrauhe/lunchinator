from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, log_error, convert_string,\
    log_warning, get_server, log_debug, get_peers, get_notification_center
import urllib2,sys,tempfile,csv,contextlib,os,socket
from lunchinator.utilities import getValidQtParent, displayNotification
from lunchinator.download_thread import DownloadThread
from StringIO import StringIO
from functools import partial
from tempfile import NamedTemporaryFile
from urlparse import urlparse
from lunchinator.peer_actions import PeerAction
from lunchinator.privacy import PrivacySettings
    
class _RemotePictureAction(PeerAction):
    def getName(self):
        return "Send Remote Picture"
    
    def getMessagePrefix(self):
        return "REMOTE_PIC"
    
    def hasCategories(self):
        return True
    
    def getPrivacyCategories(self):
        if self.getPluginObject().gui is not None:
            return self.getPluginObject().gui.getCategories()
        log_error("Remote Pictures GUI is None")
        return []
    
    def getDefaultPrivacyPolicy(self):
        return PrivacySettings.POLICY_BY_CATEGORY
    
    def getCategoryFromMessage(self, value):
        with contextlib.closing(StringIO(value.encode('utf-8'))) as strIn:
            reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
            valueList = [aValue.decode('utf-8') for aValue in reader.next()]
            if len(valueList) > 2:
                return valueList[2]
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        return RemotePicturesGui.UNCATEGORIZED
    
class remote_pictures(iface_gui_plugin):
    def __init__(self):
        super(remote_pictures, self).__init__()
        self.options = [((u"min_opacity", u"Minimum opacity of controls:", self.minOpacityChanged),20),
                        ((u"max_opacity", u"Maximum opacity of controls:", self.maxOpacityChanged),80),
                        ((u"thumbnail_size", u"Thumbnail Size:", self.thumbnailSizeChanged),150),
                        ((u"smooth_scaling", u"Smooth scaling", self.smoothScalingChanged),False)]
        self.gui = None
        self._rpAction = None
        
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
    
    def get_peer_actions(self):
        self._rpAction = _RemotePictureAction()
        return [self._rpAction]
    
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
            
    def _appendListOption(self, o, new_v):
        old_val = self.options[o]
        if len(old_val) > 0:
            val_list = old_val.split(";;")
        else:
            val_list = []
        val_list.append(new_v)
        new_val = ";;".join(val_list)
        self.set_option(o, new_val, convert=False)
            
    def privacySettingsChanged(self):
        get_notification_center().emitPrivacySettingsChanged(self._rpAction.getPluginName(), self._rpAction.getName())
            
    def process_event(self,cmd,value,_ip,_info):
        if cmd=="HELO_REMOTE_PIC":
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
