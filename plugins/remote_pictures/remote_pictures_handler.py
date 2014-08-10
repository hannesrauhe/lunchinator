from lunchinator import get_settings, convert_string,\
    log_error, log_exception, get_peers, convert_raw, log_debug
from lunchinator.callables import AsyncCall
from lunchinator.download_thread import DownloadThread
from remote_pictures.remote_pictures_storage import RemotePicturesStorage
from remote_pictures.remote_pictures_category_model import CategoriesModel
import csv, tempfile, os, urllib2, contextlib
from time import time
from cStringIO import StringIO
from functools import partial
from PyQt4.QtCore import QObject, Qt, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QImage
from lunchinator.utilities import displayNotification
from urlparse import urlparse
from lunchinator.privacy import PrivacySettings
import string

class RemotePicturesHandler(QObject):
    addCategory = pyqtSignal(object, object, int) # category, thumbnail path, thumbnail size
    categoriesChanged = pyqtSignal()
    # cat, picID, picRow, hasPrev, hasNext
    displayImageInGui = pyqtSignal(object, int, list, bool, bool)

    _loadPictures = pyqtSignal()
    _processRemotePicture = pyqtSignal(str, object, bool) # data, ip, store locally
    _checkCategory = pyqtSignal(object)
    _thumbnailSizeChanged = pyqtSignal(int)
    
    def __init__(self, thumbnailSize, gui):
        super(RemotePicturesHandler, self).__init__()

        self._thumbnailSize = thumbnailSize        
        self._gui = gui
        self._storage = RemotePicturesStorage(self)
        
        self._createThumbnailAndAddCategory = AsyncCall(self,
                                                        self._createThumbnail,
                                                        self._addCategoryAndCloseFile)
        
        self._loadPictures.connect(self._loadPicturesSlot)
        self._processRemotePicture.connect(self._processRemotePictureSlot)
        self._checkCategory.connect(self._checkCategorySlot)
        self._thumbnailSizeChanged.connect(self._thumbnailSizeChangedSlot)
    
    def loadPictures(self):
        self._loadPictures.emit()
    @pyqtSlot()
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
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        prefix = ''.join(c for c in category if c in valid_chars)
        return tempfile.NamedTemporaryFile(suffix=ext, prefix=prefix, dir=self._getPicturesDirectory(), delete=False)
    
    def _createThumbnail(self, inFile, inPath, inURL, category):
        """Called asynchronously"""
        try:
            outFile = self._createPictureFile(category)
            fileName = outFile.name
    
            if inFile:
                imageData = inFile.read()
            elif inPath and os.path.exists(inPath):
                with contextlib.closing(open(inPath, 'rb')) as inFile:
                    imageData = inFile.read()
            else:
                imageData = urllib2.urlopen(inURL.encode('utf-8')).read()
            
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
            log_exception("Error trying to create thumbnail for category")
            return None, inFile, category
            
    def _addCategoryAndCloseFile(self, aTuple):
        """Called synchronously, with result of _createThumbnail"""
        thumbnailPath, imageFile, category = aTuple
        if thumbnailPath is not None:
            # store thumbnail path in database
            self._storage.setCategoryThumbnail(category, thumbnailPath)
        self.addCategory.emit(category, thumbnailPath, self._thumbnailSize)
        if imageFile is not None:
            imageFile.close()
            
    def _addCategory(self, category, thumbnailPath=None, imageFile=None, imageURL=None):
        # cache category image
        closeImmediately = True
        try:
            if thumbnailPath != None:
                self.addCategory.emit(category, thumbnailPath, self._thumbnailSize)
            elif (imageFile and os.path.exists(imageFile)) or imageURL is not None:
                # create thumbnail asynchronously, then close imageFile
                self._createThumbnailAndAddCategory(None, imageFile, imageURL, category)
                closeImmediately = False
            else:
                raise Exception("No image path specified.")
        finally:
            if closeImmediately and imageFile != None:
                imageFile.close()

    def thumbnailSizeChanged(self, newValue):
        self._thumbnailSizeChanged.emit(newValue)
    @pyqtSlot(int)
    def _thumbnailSizeChangedSlot(self, newValue):
        self._thumbnailSize = newValue

    def checkCategory(self, cat):
        self._checkCategory.emit(cat)
    @pyqtSlot(object)
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
            self._createThumbnailAndAddCategory(imageFile, imagePath, url, category)
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
            log_error("Cannot display picture", category, "(picture not found).")
            
        self.displayImageInGui.emit(category,
                                    picID,
                                    list(picRow),
                                    self._storage.hasPrevious(category, picID),
                                    self._storage.hasNext(category, picID))
        self._storage.seenPicture(picID)
        
    def _errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % convert_string(url))
        thread.deleteLater()
        
    def _downloadedPicture(self, category, description, sender, storeLocally, thread, url):
        name = "New Remote Picture"
        if category != None:
            name = name + " in category %s" % category
            
        # create temporary image file to display in notification
        url = convert_string(url)
        thread.target.flush()
        
        displayNotification(name, description, thread.target.name)
        
        self._addPicture(thread.target,
                         thread.target.name if storeLocally else None,
                         url,
                         category,
                         description,
                         sender)
          
    def _extractPicture(self, url, category, description, sender, storeLocally):
        if not self._hasPicture(category, url):
            ext = os.path.splitext(urlparse(url.encode('utf-8')).path)[1]
            if storeLocally:
                target = self._createPictureFile(category, ext=ext)
            else:
                target = tempfile.NamedTemporaryFile(suffix=ext)
            
            downloadThread = DownloadThread(self, url, target)
            downloadThread.success.connect(partial(self._downloadedPicture, category, description, sender, storeLocally))
            downloadThread.error.connect(self._errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            log_debug("Remote Pics: Downloaded this url before, won't do it again:",url)
        
    def processRemotePicture(self, value, ip, storeLocally):
        self._processRemotePicture.emit(value, ip, storeLocally)
    @pyqtSlot(str, object, bool)
    def _processRemotePictureSlot(self, value, ip, storeLocally):
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
        
        self._extractPicture(url, cat, desc, get_peers().getPeerID(pIP=ip), storeLocally)    
    
    def getCategories(self, alsoEmpty):
        return self._storage.getCategories(alsoEmpty)
    
    def getCategoryNames(self, alsoEmpty):
        return self._storage.getCategoryNames(alsoEmpty)
    
    def willIgnorePeerAction(self, category, url):
        return self._hasPicture(category, url)

    ################# PUBLIC SLOTS ##################
        
    @pyqtSlot(object)   
    def openCategory(self, category):
        category = convert_string(category)
        if not self._storage.hasCategory(category):
            log_error("Cannot open category", category, "(category not found).")
            return
        
        self._displayImage(category, self._storage.getLatestPicture(category))
    
    @pyqtSlot(object, int)
    def displayPrev(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getPreviousPicture(cat, curID))
    
    @pyqtSlot(object, int)
    def displayNext(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getNextPicture(cat, curID))    
