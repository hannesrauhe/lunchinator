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

class RemotePicturesHandler(QObject):
    addCategory = pyqtSignal(unicode, unicode, int) # category, thumbnail path, thumbnail size
    categoriesChanged = pyqtSignal()
    # cat, picID, picURL, picFile, picDesc, hasPrev, hasNext
    displayImageInGui = pyqtSignal(unicode, int, unicode, unicode, unicode, bool, bool)

    _loadPictures = pyqtSignal()
    _processRemotePicture = pyqtSignal(str, unicode) # data, ip
    _checkCategory = pyqtSignal(unicode)
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
        return get_settings().get_config("remote_pictures")
    
    def _fileForThumbnail(self, _category):
        return tempfile.NamedTemporaryFile(suffix='.jpg', dir=self._getPicturesDirectory(), delete=False)
    
    def _createThumbnail(self, inFile, inURL, category):
        """Called asynchronously"""
        outFile = self._fileForThumbnail(category)
        fileName = outFile.name

        try:        
            if inFile and os.path.exists(inFile):
                imageData = inFile.read()
            else:
                imageData = urllib2.urlopen(inURL.encode('utf-8')).read()
        except:
            log_exception("Error reading data for category thumbnail.")
            return None, inFile, category
        
        oldImage = QImage.fromData(imageData)
        if oldImage.width() > CategoriesModel.MAX_THUMBNAIL_SIZE or oldImage.height() > CategoriesModel.MAX_THUMBNAIL_SIZE:
            newImage = oldImage.scaled(CategoriesModel.MAX_THUMBNAIL_SIZE,
                                       CategoriesModel.MAX_THUMBNAIL_SIZE,
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
                self._createThumbnailAndAddCategory(imageFile, imageURL, category)
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
    @pyqtSlot(unicode)
    def _checkCategorySlot(self, cat):
        cat = convert_string(cat)
        if not self._storage.hasCategory(cat):
            self._storage.addEmptyCategory(cat)
            self.categoriesChanged.emit()

    def _addPicture(self, imageFile, url, category, description, sender):
        if category == None:
            category = self.UNCATEGORIZED

        catAdded = self._storage.addPicture(category,
                                            url if url else None,
                                            description if description else None,
                                            None, # TODO locally stored image
                                            time(),
                                            None,
                                            sender if sender else None)
        
        if catAdded:
            self._createThumbnailAndAddCategory(None, url, category) # TODO local image
            
        if self._gui.isShowingCategory(category):
            # if category is open, display image immediately
            picID = self._storage.getPictureID(category, url)
            if picID is None:
                log_error("Cannot display picture (not found)")
                return
            self.displayImageInGui.emit(category,
                                        picID,
                                        url,
                                        u"", # TODO locally stored image
                                        description,
                                        self._storage.hasPrevious(category, picID),
                                        False)
    
    def _hasPicture(self, cat, url):
        return self._storage.hasPicture(cat, url)
            
    def _displayImage(self, category, result):
        picID, picRow = result
        if picID is None:
            log_error("Cannot display picture", category, "(picture not found).")
            
        picURL = picRow[RemotePicturesStorage.PIC_URL_COL]
        picFile = picRow[RemotePicturesStorage.PIC_FILE_COL]
        picDesc = picRow[RemotePicturesStorage.PIC_DESC_COL]
        self.displayImageInGui.emit(category,
                                    picID,
                                    picURL if picURL else u"",
                                    picFile if picFile else u"",
                                    picDesc if picDesc else u"",
                                    self._storage.hasPrevious(category, picID),
                                    self._storage.hasNext(category, picID))
         
    @pyqtSlot(unicode)   
    def openCategory(self, category):
        category = convert_string(category)
        if not self._storage.hasCategory(category):
            log_error("Cannot open category", category, "(category not found).")
        
        self._displayImage(category, self._storage.getLatestPicture(category))
    
    @pyqtSlot(unicode, int)
    def displayPrev(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getPreviousPicture(cat, curID))
    
    @pyqtSlot(unicode, int)
    def displayNext(self, cat, curID):
        cat = convert_string(cat)
        self._displayImage(cat, self._storage.getNextPicture(cat, curID))
        
    def _errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % convert_string(url))
        thread.deleteLater()
        
    def _downloadedPicture(self, category, description, sender, thread, url):
        name = "New Remote Picture"
        if category != None:
            name = name + " in category %s" % category
            
        # create temporary image file to display in notification
        url = convert_string(url)
        ext = os.path.splitext(urlparse(url.encode('utf-8')).path)[1]
        newFile = tempfile.NamedTemporaryFile(suffix=ext)
        newFile.write(thread.getResult())
        newFile.seek(0)
        displayNotification(name, description, newFile.name)
        
        # TODO close file
        self._addPicture(newFile, url, category, description, sender)
          
    def _extractPicture(self, url, category, description, sender):
        if not self._hasPicture(category, url):
            downloadThread = DownloadThread(self, url)
            downloadThread.success.connect(partial(self._downloadedPicture, category, description, sender))
            downloadThread.error.connect(self._errorDownloadingPicture)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        else:
            log_debug("Remote Pics: Downloaded this url before, won't do it again:",url)
        
    def processRemotePicture(self, value, ip):
        self._processRemotePicture.emit(value, ip)
    @pyqtSlot(str, unicode)
    def _processRemotePictureSlot(self, value, ip):
        value = convert_raw(value)
        ip = convert_string(ip)
        with contextlib.closing(StringIO(value)) as strIn:
            reader = csv.reader(strIn, delimiter = ' ', quotechar = '"')
            valueList = [aValue.decode('utf-8') for aValue in reader.next()]
            url = valueList[0]
            desc = None
            cat = None
            if len(valueList) > 1:
                desc = valueList[1]
            if len(valueList) > 2:
                cat = valueList[2]
        
        self._extractPicture(url, cat, desc, get_peers().getPeerID(pIP=ip))    
    
    def getCategories(self, alsoEmpty):
        return self._storage.getCategories(alsoEmpty)
    
    def getCategoryNames(self, alsoEmpty):
        return self._storage.getCategoryNames(alsoEmpty)