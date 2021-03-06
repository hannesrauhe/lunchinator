from remote_pictures.remote_pictures_storage import RemotePicturesStorage
from remote_pictures.remote_pictures_category_model import CategoriesModel
from lunchinator import get_settings, convert_string, get_peers, convert_raw
from lunchinator.log import loggingFunc
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.callables import AsyncCall
from lunchinator.download_thread import DownloadThread
from lunchinator.privacy import PrivacySettings
from lunchinator.utilities import displayNotification, sanitizeForFilename

from PyQt4.QtCore import QObject, Qt, pyqtSignal, QThread
from PyQt4.QtGui import QImage

import csv, tempfile, os, urllib2, contextlib
from time import time
from cStringIO import StringIO
from functools import partial
from urlparse import urlparse
from lunchinator.logging_mutex import loggingMutex

class RemotePicturesHandler(QObject):
    addCategory = pyqtSignal(object, object, int) # category, thumbnail path, thumbnail size
    categoryThumbnailChanged = pyqtSignal(object, object, int) # category, thumbnail path, thumbnail size
    categoriesChanged = pyqtSignal()
    # cat, picID, picRow, hasPrev, hasNext
    displayImageInGui = pyqtSignal(object, int, list, bool, bool)

    _loadPictures = pyqtSignal()
    _processRemotePicture = pyqtSignal(str, object) # data, ip
    _checkCategory = pyqtSignal(object)
    _thumbnailSizeChanged = pyqtSignal(int)
    _storeLocallyChanged = pyqtSignal(bool)
    
    def __init__(self, logger, thumbnailSize, storeLocally, gui):
        super(RemotePicturesHandler, self).__init__()

        self.logger = logger
        self._thumbnailSize = thumbnailSize
        self._storeLocally = storeLocally 
        self._gui = gui
        self._storage = RemotePicturesStorage(self, self.logger)
        self._currentlyDownloading = set() # set of currently downloading pictures
        self._lock = loggingMutex(u"Remote Pictures Handler", qMutex=True, logging=get_settings().get_verbose())
        
        self._createThumbnailAndAddCategory = AsyncCall(self,
                                                        self.logger,
                                                        self._createThumbnail,
                                                        self._addCategoryAndCloseFile)
        
        self._createAndChangeThumbnail = AsyncCall(self,
                                                   self.logger,
                                                   self._createThumbnail,
                                                   self._changeThumbnail)
        
        self._loadPictures.connect(self._loadPicturesSlot)
        self._processRemotePicture.connect(self._processRemotePictureSlot)
        self._checkCategory.connect(self._checkCategorySlot)
        self._thumbnailSizeChanged.connect(self._thumbnailSizeChangedSlot)
        self._storeLocallyChanged.connect(self._storeLocallyChangedSlot)
    
    def loadPictures(self):
        self._loadPictures.emit()
    @loggingSlot()
    def _loadPicturesSlot(self):
        categories = self._storage.getCategories(alsoEmpty=False)
        for row in categories:
            category = row[RemotePicturesStorage.CAT_TITLE_COL]
            thumbnailPath = row[RemotePicturesStorage.CAT_THUMBNAIL_COL]
            
            picFile = None
            picURL = None
            if not thumbnailPath or not os.path.exists(thumbnailPath):
                thumbnailPath = None
                
                # create thumbnail from first image
                _picID, picRow = self._storage.getLatestPicture(category)
                picFile = picRow[RemotePicturesStorage.PIC_FILE_COL]
                if picFile and os.path.exists(picFile):
                    picFile = picRow[RemotePicturesStorage.PIC_FILE_COL]
                else:
                    picURL = picRow[RemotePicturesStorage.PIC_URL_COL]
                
            self._addCategory(category,
                              thumbnailPath=thumbnailPath,
                              imageFile=picFile,
                              imageURL=picURL)
    
    def finish(self):
        pass
    
    def _getPicturesDirectory(self):
        picDir = get_settings().get_config("remote_pictures")
        if not os.path.exists(picDir):
            os.makedirs(picDir)
        return picDir
    
    def _createPictureFile(self, category, ext='.jpg'):
        prefix = sanitizeForFilename(category)
        return tempfile.NamedTemporaryFile(suffix=ext, prefix=prefix, dir=self._getPicturesDirectory(), delete=False)
    
    def _createThumbnail(self, inFile, inPath, inURL, inImage, category):
        """Called asynchronously"""
        try:
            fileName = None
            
            # if category already has a thumbnail, overwrite
            curPath = self._storage.getCategoryThumbnail(category)
            if curPath is not None:
                try:
                    # check if we can write the file
                    open(curPath, 'wb').close()
                    fileName = curPath
                except:
                    pass
            
            if fileName is None:
                outFile = self._createPictureFile(category)
                fileName = outFile.name
                outFile.close()
            
            oldImage = None
            imageData = None
            if inImage:
                oldImage = inImage
            elif inFile:
                imageData = inFile.read()
            elif inPath and os.path.exists(inPath):
                with contextlib.closing(open(inPath, 'rb')) as inFile:
                    imageData = inFile.read()
            else:
                imageData = urllib2.urlopen(inURL.encode('utf-8')).read()
            
            if oldImage is None:
                oldImage = QImage.fromData(imageData)
            if oldImage.width() > CategoriesModel.MAX_THUMBNAIL_SIZE or oldImage.height() > CategoriesModel.MAX_THUMBNAIL_SIZE:
                newImage = oldImage.scaled(CategoriesModel.MAX_THUMBNAIL_SIZE,
                                           CategoriesModel.MAX_THUMBNAIL_SIZE,
                                           Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation)
            else:
                # no up-scaling here
                newImage = oldImage
            newImage.save(fileName, 'jpeg')
            return fileName, inFile, category
        except:
            self.logger.exception("Error trying to create thumbnail for category")
            return None, inFile, category
            
    def __setCategoryThumbnail(self, thumbnailPath, imageFile, category):
        if thumbnailPath is not None:
            # store thumbnail path in database
            self._storage.setCategoryThumbnail(category, thumbnailPath)
        if imageFile is not None:
            imageFile.close()
    
    @loggingSlot(object)
    def _addCategoryAndCloseFile(self, aTuple):
        """Called synchronously, with result of _createThumbnail"""
        thumbnailPath, imageFile, category = aTuple
        self.__setCategoryThumbnail(thumbnailPath, imageFile, category)
        self.addCategory.emit(category, thumbnailPath, self._thumbnailSize)
            
    @loggingSlot(object)
    def _changeThumbnail(self, aTuple):
        """Called synchronously, with result of _createThumbnail"""
        thumbnailPath, imageFile, category = aTuple
        self.__setCategoryThumbnail(thumbnailPath, imageFile, category)
        self.categoryThumbnailChanged.emit(category, thumbnailPath, self._thumbnailSize)
            
    def _addCategory(self, category, thumbnailPath=None, imageFile=None, imageURL=None):
        # cache category image
        closeImmediately = True
        try:
            if thumbnailPath != None:
                self.addCategory.emit(category, thumbnailPath, self._thumbnailSize)
            elif (imageFile and os.path.exists(imageFile)) or imageURL is not None:
                # create thumbnail asynchronously, then close imageFile
                self._createThumbnailAndAddCategory(None, imageFile, imageURL, None, category)
                closeImmediately = False
            else:
                raise Exception("No image path specified.")
        finally:
            if closeImmediately and imageFile != None:
                imageFile.close()

    def thumbnailSizeChanged(self, newValue):
        self._thumbnailSizeChanged.emit(newValue)
    @loggingSlot(int)
    def _thumbnailSizeChangedSlot(self, newValue):
        self._thumbnailSize = newValue
        
    def storeLocallyChanged(self, newValue):
        self._storeLocallyChanged.emit(newValue)
    @loggingSlot(bool)
    def _storeLocallyChangedSlot(self, newValue):
        self._storeLocally = newValue

    def checkCategory(self, cat):
        self._checkCategory.emit(cat)
    @loggingSlot(object)
    def _checkCategorySlot(self, cat):
        cat = convert_string(cat)
        if not self._storage.hasCategory(cat):
            self._storage.addEmptyCategory(cat)
            self.categoriesChanged.emit()

    def _addPicture(self, imageFile, imagePath, url, category, description, sender):
        if category == None:
            category = PrivacySettings.NO_CATEGORY

        catAdded = self._storage.addPicture(category,
                                            url if url else None,
                                            description if description else None,
                                            imagePath,
                                            time(),
                                            None,
                                            sender if sender else None)
        
        if catAdded:
            if imageFile is not None:
                imageFile.seek(0)
            # image file will be closed after thumbnail was created
            self._createThumbnailAndAddCategory(imageFile, imagePath, url, None, category)
        elif imageFile is not None:
            imageFile.close()
            
        if self._gui.isShowingCategory(category):
            # if category is open, display image immediately
            self._displayImage(category, self._storage.getLatestPicture(category))
    
    def _hasPicture(self, cat, url):
        return self._storage.hasPicture(cat, url)
            
    def _displayImage(self, category, result):
        picID, picRow = result
        if picID is None:
            self.logger.error("Cannot display picture %d (picture not found).", picID)
            
        self.displayImageInGui.emit(category,
                                    picID,
                                    list(picRow),
                                    self._storage.hasPrevious(category, picID),
                                    self._storage.hasNext(category, picID))
        self._storage.seenPicture(picID)
        
    @loggingSlot(QThread, object)
    def _errorDownloadingPicture(self, thread, err):
        self.logger.error("Error downloading picture from url %s: %s", convert_string(thread.url), err)
        thread.deleteLater()
        
    @loggingFunc
    def _downloadedPicture(self, category, description, sender, thread, url):
        if self._hasPicture(category, url):
            self.logger.warning("Picture already in storage: %s", url)
            return
        
        name = "New Remote Picture"
        if category != None:
            name = name + " in category %s" % category
            
        # create temporary image file to display in notification
        url = convert_string(url)
        thread.target.flush()
        
        displayNotification(name, description, self.logger, thread.target.name)
        
        self._addPicture(thread.target,
                         thread.target.name if self._storeLocally else None,
                         url,
                         category,
                         description,
                         sender)
          
    def _extractPicture(self, url, category, description, sender):
        if not self._hasPicture(category, url):
            ext = os.path.splitext(urlparse(url.encode('utf-8')).path)[1]
            if self._storeLocally:
                target = self._createPictureFile(category, ext=ext)
            else:
                target = tempfile.NamedTemporaryFile(suffix=ext)
            
            downloadThread = DownloadThread(self, self.logger, url, target)
            downloadThread.success.connect(partial(self._downloadedPicture, category, description, sender))
            downloadThread.error.connect(self._errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            self.logger.debug("Remote Pics: Downloaded this url before, won't do it again: %s", url)
        
    def processRemotePicture(self, value, ip):
        self._processRemotePicture.emit(value, ip)
    @loggingSlot(str, object)
    def _processRemotePictureSlot(self, value, ip):
        value = convert_raw(value)
        ip = convert_string(ip)
        with contextlib.closing(StringIO(value)) as strIn:
            reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
            valueList = [aValue.decode('utf-8') for aValue in reader.next()]
            url = valueList[0]
            desc = None
            cat = PrivacySettings.NO_CATEGORY
            if len(valueList) > 1:
                desc = valueList[1]
            if len(valueList) > 2:
                cat = valueList[2]
        
        self._lock.lock()
        try:
            if url in self._currentlyDownloading:
                self.logger.debug("Already downloading picture %s", url)
                return
            self._currentlyDownloading.add(url)
        finally:
            self._lock.unlock()
        
        self._extractPicture(url, cat, desc, get_peers().getPeerID(pIP=ip))    
    
    def getCategories(self, alsoEmpty):
        return self._storage.getCategories(alsoEmpty)
    
    def getCategoryNames(self, alsoEmpty):
        return self._storage.getCategoryNames(alsoEmpty)
    
    def willIgnorePeerAction(self, category, url):
        self._lock.lock()
        try:
            if url in self._currentlyDownloading:
                return True
        finally:
            self._lock.unlock()
        return self._hasPicture(category, url)

    ################# PUBLIC SLOTS ##################
        
    @loggingSlot(object)   
    def openCategory(self, category):
        category = convert_string(category)
        if not self._storage.hasCategory(category):
            self.logger.error("Cannot open category %s (category not found).", category)
            return
        
        self._displayImage(category, self._storage.getLatestPicture(category))
    
    @loggingSlot(object, int)
    def displayPrev(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getPreviousPicture(cat, curID))
    
    @loggingSlot(object, int)
    def displayNext(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getNextPicture(cat, curID))    

    @loggingSlot(object, object, object)
    def pictureDownloaded(self, category, url, picData):
        if self._storeLocally:
            ext = os.path.splitext(urlparse(url.encode('utf-8')).path)[1]
            with contextlib.closing(self._createPictureFile(category, ext)) as picFile:
                picFile.write(picData)
                self._storage.setPictureFile(category, url, picFile.name)
    
    @loggingSlot(object, QImage)
    def setCategoryThumbnail(self, category, image):
        self._createAndChangeThumbnail(None, None, None, image, category)
        