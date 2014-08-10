from lunchinator.plugin import iface_gui_plugin
from lunchinator import log_exception, get_settings, log_error, convert_string,\
    log_warning, get_server, log_debug, get_peers, get_notification_center
import urllib2,sys,tempfile,csv,contextlib,os,socket
from lunchinator.utilities import getValidQtParent, displayNotification,\
    canUseBackgroundQThreads
from lunchinator.download_thread import DownloadThread
from StringIO import StringIO
from functools import partial
from tempfile import NamedTemporaryFile
from urlparse import urlparse
from lunchinator.peer_actions import PeerAction
from lunchinator.privacy import PrivacySettings
from remote_pictures.remote_pictures_dialog import RemotePicturesDialog
    
class _RemotePictureAction(PeerAction):
    def getName(self):
        return "Send Remote Picture"
    
    def appliesToPeer(self, _peerID, _peerInfo):
        return True
    
    def performAction(self, peerID, peerInfo, parent):
        self.getPluginObject().sendRemotePicture(peerID, peerInfo, parent)
    
    def getMessagePrefix(self):
        return "REMOTE_PIC"
    
    def hasCategories(self):
        return True
    
    def getPrivacyCategories(self):
        return self.getPluginObject().getCategories()
    
    def hasPrivacyCategory(self, _category):
        # we add categories dynamically
        return True
    
    def getCategoryIcon(self, category):
        return self.getPluginObject().getCategoryIcon(category)
    
    def getDefaultPrivacyPolicy(self):
        return PrivacySettings.POLICY_BY_CATEGORY
    
    def willIgnorePeerAction(self, value):
        with contextlib.closing(StringIO(value.encode('utf-8'))) as strIn:
            reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
            valueList = [aValue.decode('utf-8') for aValue in reader.next()]
            url = valueList[0]
            cat = PrivacySettings.NO_CATEGORY
            if len(valueList) > 2:
                cat = valueList[2]
            return self.getPluginObject().willIgnorePeerAction(cat, url)
    
    def getCategoryFromMessage(self, value):
        with contextlib.closing(StringIO(value.encode('utf-8'))) as strIn:
            reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
            valueList = [aValue.decode('utf-8') for aValue in reader.next()]
            if len(valueList) > 2:
                self.getPluginObject().checkCategory(valueList[2])
                return valueList[2]
        return PrivacySettings.NO_CATEGORY
    
class remote_pictures(iface_gui_plugin):
    VERSION_DB = 0
    VERSION_CURRENT = VERSION_DB
    
    def __init__(self):
        super(remote_pictures, self).__init__()
        self.options = [((u"min_opacity", u"Minimum opacity of controls:", self.minOpacityChanged), 20),
                        ((u"max_opacity", u"Maximum opacity of controls:", self.maxOpacityChanged), 80),
                        ((u"thumbnail_size", u"Thumbnail Size:", self.thumbnailSizeChanged), 150),
                        ((u"smooth_scaling", u"Smooth scaling", self.smoothScalingChanged), False),
                        ((u"store_locally", u"Store pictures locally"), True)]
        self._gui = None
        self._handler = None
        self._rpAction = None
        
    def _handleOpacity(self, newValue, signal):
        if newValue < 0:
            newValue = 0
        elif newValue > 100:
            newValue = 100
            
        if signal is not None:
            signal.emit(float(newValue) / 100.)
        return newValue
        
    def minOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, None if self._gui is None else self._gui.minOpacityChanged)
    
    def maxOpacityChanged(self, _setting, newValue):
        return self._handleOpacity(newValue, None if self._gui is None else self._gui.maxOpacityChanged)
    
    def thumbnailSizeChanged(self, _setting, newValue):
        from remote_pictures.remote_pictures_category_model import CategoriesModel
        if newValue < CategoriesModel.MIN_THUMBNAIL_SIZE:
            newValue = CategoriesModel.MIN_THUMBNAIL_SIZE
        elif newValue > CategoriesModel.MAX_THUMBNAIL_SIZE:
            newValue = CategoriesModel.MAX_THUMBNAIL_SIZE
        
        if self._gui is not None:
            self._gui.thumbnailSizeChanged(newValue)
        if self._handler is not None:
            self._handler.thumbnailSizeChanged(newValue)
        return newValue
        
    def smoothScalingChanged(self, _setting, newValue):
        if self._gui is not None:
            self._gui.setSmoothScaling(newValue)
        
    def create_widget(self, parent):
        from PyQt4.QtCore import QThread
        from remote_pictures.remote_pictures_gui import RemotePicturesGui
        from remote_pictures.remote_pictures_handler import RemotePicturesHandler
        super(remote_pictures, self).create_widget(parent)
        self._gui = RemotePicturesGui(parent,
                                      self.get_option(u"smooth_scaling"),
                                      self.get_option(u"min_opacity"),
                                      self.get_option(u"max_opacity"))
        
        if canUseBackgroundQThreads():
            self._messagesThread = QThread()
        else:
            self._messagesThread = None
        self._handler = RemotePicturesHandler(self.get_option(u"thumbnail_size"), self._gui)
        if self._messagesThread is not None:
            self._handler.moveToThread(self._messagesThread)
            self._messagesThread.start()
        
        self._gui.openCategory.connect(self._handler.openCategory)
        self._gui.displayPrev.connect(self._handler.displayPrev)
        self._gui.displayNext.connect(self._handler.displayNext)
        
        self._handler.addCategory.connect(self._gui.categoryModel.addCategory)
        self._handler.displayImageInGui.connect(self._gui.displayImage)
        
        self._gui.categoryModel.categoriesChanged.connect(self._privacySettingsChanged)
        self._handler.categoriesChanged.connect(self._privacySettingsChanged)
        
        self._handler.loadPictures()
        
        return self._gui
    
    def destroy_widget(self):
        if self._gui is not None and self._handler is not None:
            self._gui.openCategory.disconnect(self._handler.openCategory)
            self._gui.displayPrev.disconnect(self._handler.displayPrev)
            self._gui.displayNext.disconnect(self._handler.displayNext)
            
            self._handler.addCategory.disconnect(self._gui.categoryModel.addCategory)
            self._handler.displayImageInGui.disconnect(self._gui.displayImage)
            
        if self._gui is not None:
            self._gui.categoryModel.categoriesChanged.disconnect(self._privacySettingsChanged)
            self._gui.destroyWidget()
        
        if self._handler is not None:
            self._handler.categoriesChanged.disconnect(self._privacySettingsChanged)
            self._handler.finish()
            
        if self._messagesThread is not None:
            self._messagesThread.quit()
            self._messagesThread.wait()
            self._messagesThread.deleteLater()
        
        iface_gui_plugin.destroy_widget(self)

    def extendsInfoDict(self):
        return True
        
    def extendInfoDict(self, infoDict):
        infoDict[u"RP_v"] = self.VERSION_CURRENT
        
    def get_peer_actions(self):
        self._rpAction = _RemotePictureAction()
        return [self._rpAction]
            
    def checkCategory(self, cat):
        if self._handler is not None:
            self._handler.checkCategory(cat)
            
    def process_event(self, cmd, value, ip, _info):
        if cmd=="HELO_REMOTE_PIC":
            if self._handler is not None:
                self._handler.processRemotePicture(value, ip, self.get_option(u"store_locally"))
    
    def getCategories(self):
        if self._handler is None:
            log_error("Remote Pictures not initialized")
            return []
    
        return self._handler.getCategoryNames(alsoEmpty=True)
    
    def getCategoryIcon(self, category):
        if self._gui is None:
            log_error("Remote Pictures not initialized")
            return None
        return self._gui.getCategoryIcon(category)
    
    def willIgnorePeerAction(self, category, url):
        return self._handler.willIgnorePeerAction(category, url)
    
    def sendRemotePicture(self, peerID, peerInfo, parent):
        dialog = RemotePicturesDialog(parent, peerID, peerInfo)
        result = dialog.exec_()
        if result == RemotePicturesDialog.Accepted:
            data = [dialog.getURL().encode('utf-8')]
            if dialog.getDescription():
                data.append(dialog.getDescription().encode('utf-8'))
                if dialog.getCategory():
                    data.append(dialog.getCategory().encode('utf-8'))
            get_server().call("HELO_REMOTE_PIC " + ' '.join(data), peerIDs=[peerID])
    
    def _privacySettingsChanged(self):
        get_notification_center().emitPrivacySettingsChanged(self._rpAction.getPluginName(), self._rpAction.getName())
