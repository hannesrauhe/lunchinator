from PyQt4.QtCore import QObject, Qt, pyqtSignal
from lunchinator import get_settings, get_notification_center, convert_string,\
    log_error
from remote_pictures.remote_pictures_storage import RemotePicturesStorage
import tempfile
from lunchinator.callables import AsyncCall
from remote_pictures.remote_pictures_category_model import CategoriesModel
from PyQt4.QtGui import QImage
from time import time

class RemotePicturesHandler(QObject):
    # cat, picID, picURL=None, picFile=None, picDesc=None, hasPrev=False, hasNext=False
    displayImage = pyqtSignal(unicode, int, unicode, unicode, unicode, bool, bool)
    
    def __init__(self, delegate, gui):
        super(RemotePicturesHandler, self).__init__()
        
        self._delegate = delegate
        self._storage = RemotePicturesStorage(self)
        self._gui = gui
        self._categoryModel = CategoriesModel()
        self._gui.setModel(self._categoryModel)
        
        self._gui.openCategory.connect(self._openCategory)
        self._gui.displayPrev.connect(self._displayPrev)
        self._gui.displayNext.connect(self._displayNext)
        
        self._createThumbnailAndAddCategory = AsyncCall(self,
                                                        self._createThumbnail,
                                                        self._addCategoryAndCloseFile)
        
        # TODO add categories
    
    def finish(self):
        pass
    
    def getPicturesDirectory(self):
        return get_settings().get_config("remote_pictures")
    
    def getIndexFile(self):
        return get_settings().get_config("remote_pictures", "index")
    
    def _fileForThumbnail(self, _category):
        return tempfile.NamedTemporaryFile(suffix='.jpg', dir=self._picturesDirectory(), delete=False)
    
    def _createThumbnail(self, inFile, category):
        """Called asynchronously"""
        outFile = self._fileForThumbnail(category)
        fileName = outFile.name
        
        imageData = inFile.read()
        oldImage = QImage.fromData(imageData)
        if oldImage.width() > self.MAX_THUMBNAIL_SIZE or oldImage.height() > self.MAX_THUMBNAIL_SIZE:
            newImage = oldImage.scaled(self.MAX_THUMBNAIL_SIZE,
                                       self.MAX_THUMBNAIL_SIZE,
                                       Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation)
        else:
            # no up-scaling here
            newImage = oldImage
        newImage.save(fileName, format='jpeg')
        return fileName, inFile, category
            
    def _addCategoryAndCloseFile(self, aTuple):
        """Called synchronously, with result of _createThumbnail"""
        thumbnailPath, imageFile, category = aTuple
        self._categoryModel.addCategory(category, thumbnailPath, self._delegate.getThumbnailSize())
        imageFile.close()
            
    def _addCategory(self, category, thumbnailPath = None, imageFile = None):
        # cache category image
        closeImmediately = True
        try:
            if thumbnailPath != None:
                self._categoryModel.addCategory(category, thumbnailPath, self._delegate.getThumbnailSize())
            elif imageFile != None:
                # create thumbnail asynchronously, then close imageFile
                self._createThumbnailAndAddCategory(imageFile, category)
                closeImmediately = False
            else:
                raise Exception("No image path specified.")
            
            if not self._storage.hasCategory(category):
                self._storage.addCategory(category, thumbnailPath)
        finally:
            if closeImmediately and imageFile != None:
                imageFile.close()

    def addPicture(self, imageFile, url, category, description):
        imageFile = convert_string(imageFile)
        url = convert_string(url)
        category = convert_string(category)
        description = convert_string(description)
        
        if category == None:
            category = self.UNCATEGORIZED
        if self._storage.hasCategory(category):
            self._addCategory(category, imageFile = imageFile)
            self._privacySettingsChanged()

        self._storage.addPicture(category, url, description, None, time(), None, None) # TODO sender information
        if self._gui.isShowingCategory(category):
            # if category is open, display image immediately
            picID = self._storage.getPictureID(category, url)
            self.displayImage.emit(category,
                                   picID,
                                   url,
                                   None,
                                   description,
                                   self._storage.hasPrevious(category, picID),
                                   False)
            
    def hasPicture(self, cat, url):
        return self._storage.hasPicture(cat, url)
            
    def _openCategory(self, category):
        if not self._storage.hasCategory(category):
            log_error("Cannot open category", category, "(category not found).")
        
        latestPictureRow, picID = self._storage.getLatestPicture(category)
        if picID is None:
            log_error("Cannot open category", category, "(category empty).")
            
        self.displayImage.emit(category,
                               picID,
                               latestPictureRow[RemotePicturesStorage.PIC_URL_COL],
                               latestPictureRow[RemotePicturesStorage.PIC_FILE_COL],
                               latestPictureRow[RemotePicturesStorage.PIC_DESC_COL],
                               self._storage.hasPrevious(category, picID),
                               False)
        
    
    def _displayPrev(self, curID):
        pass # TODO
    
    def _displayNext(self, curID):
        pass # TODO
            
    def _privacySettingsChanged(self):
        get_notification_center().emitPrivacySettingsChanged(self._rpAction.getPluginName(), self._rpAction.getName())