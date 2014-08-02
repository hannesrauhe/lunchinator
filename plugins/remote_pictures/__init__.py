from lunchinator.plugin import iface_gui_plugin
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
    
    def appliesToPeer(self, _peerID, _peerInfo):
        # TODO have to implement performAction
        return False
    
    def getMessagePrefix(self):
        return "REMOTE_PIC"
    
    def hasCategories(self):
        return True
    
    def getPrivacyCategories(self):
        if self.getPluginObject().gui is not None:
            return self.getPluginObject().gui.getCategories()
        log_error("Remote Pictures GUI is None")
        return []
    
    def getCategoryIcon(self, category):
        if self.getPluginObject().gui is not None:
            return self.getPluginObject().gui.getCategoryIcon(category)
        log_error("Remote Pictures GUI is None")
        return None
    
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
        self._gui = None
        self._handler = None
        self._rpAction = None
        
    def _handleOpacity(self, newValue, signal):
        if newValue < 0:
            newValue = 0
        elif newValue > 100:
            newValue = 100
            
        signal.emit(float(newValue) / 100.)
        return newValue
        
    def minOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, self._gui.minOpacityChanged)
    
    def maxOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, self._gui.maxOpacityChanged)
    
    def thumbnailSizeChanged(self, _setting, newValue):
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        if newValue < RemotePicturesGui.MIN_THUMBNAIL_SIZE:
            newValue = RemotePicturesGui.MIN_THUMBNAIL_SIZE
        elif newValue > RemotePicturesGui.MAX_THUMBNAIL_SIZE:
            newValue = RemotePicturesGui.MAX_THUMBNAIL_SIZE
        
        self._gui.thumbnailSizeChanged(newValue)
        return newValue
        
    def smoothScalingChanged(self, _setting, newValue):
        self._gui.setSmoothScaling(newValue)
        
    def getThumbnailSize(self):
        return self.get_option(u'thumbnail_size')
    
    def create_widget(self, parent):
        from PyQt4.QtCore import QThread
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        from remote_pictures.remote_pictures_handler import RemotePicturesHandler
        super(remote_pictures, self).create_widget(parent)
        self._gui = RemotePicturesGui(parent,
                                      self.get_option(u"smooth_scaling"),
                                      self.get_option(u"min_opacity"),
                                      self.get_option(u"max_opacity"))
        
        self._messagesThread = QThread()
        self._handler = RemotePicturesHandler(self, self, self._gui)
        self._handler.moveToThread(self._messagesThread)
        self._messagesThread.start()
        
        return self._gui
    
    def destroy_widget(self):
        self._handler.finish()
        self._messagesThread.quit()
        self._messagesThread.wait()
        self._messagesThread.deleteLater()
        self._gui.destroyWidget()
        
        iface_gui_plugin.destroy_widget(self)

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
        
        self._handler.addPicture(newFile, url, category, description)
          
    def extract_pic(self,url,category,description):
        try:
            getValidQtParent()
        except:
            log_warning("Remote Pictures does not work without QT")
            return
        if not self._handler.hasPicture(category, url):
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
