import urllib2, sys, shutil
from lunchinator import log_exception, get_settings, convert_string
from PyQt4.QtGui import QImage, QPixmap, QStackedWidget, QIcon, QListView, QStandardItemModel, QStandardItem
from PyQt4.QtCore import QTimer, QSize, Qt, QVariant, QSettings, QIODevice
from lunchinator.resizing_image_label import ResizingImageLabel
import tempfile
import os
import urlparse
from docutils.parsers.rst.directives import path
import contextlib
from lunchinator.table_models import TableModelBase

class RemotePicturesGui(QStackedWidget):
    THUMBNAIL_SIZE = 200
    
    def __init__(self,parent):
        super(RemotePicturesGui, self).__init__(parent)
        
        self.good = True
        self.settings = None
        self.categoryPictures = {}

        if not os.path.exists(self._picturesDirectory()):
            try:
                os.makedirs(self._picturesDirectory())
            except:
                log_exception("Could not create remote pictures directory '%s'" % self._picturesDirectory())
                self.good = False
                
        self.categoryModel = CategoriesModel()
        
        self.categoryView = QListView(self)
        self.categoryView.setModel(self.categoryModel)
        self.categoryView.setViewMode(QListView.IconMode);
        self.categoryView.setIconSize(QSize(200,200));
        self.categoryView.setResizeMode(QListView.Adjust);

        self.addWidget(self.categoryView)
                
        # load categories index
        self._loadIndex()        

        #TODO remove        
        #self.addPicture("/Users/Corny/Pictures/Hintergrundbilder/WallpaperWizard-1740538570.jpg", "anUrl.jpg", "Category 1")
        #self.categoryModel.addCategory("Category 2", "/home/corny/Bilder/Okay.png")
        self._saveIndex()
        
    def _loadIndex(self):
        if self.good:
            try:
                self.settings = QSettings(os.path.join(self._picturesDirectory(), u"index"), QSettings.NativeFormat)
                storedCategories = self.settings.value("categoryPictures", None)
                if storedCategories != None:
                    self.categoryPictures = TableModelBase.convertDict(storedCategories.toMap())
                    
                storedThumbnails  = self.settings.value("categoryThumbnails", None)
                if storedThumbnails != None:
                    storedThumbnails = storedThumbnails.toMap()
                    for aCat in storedThumbnails:
                        self._addCategory(convert_string(aCat), thumbnailPath=convert_string(storedThumbnails[aCat].toString()))
            except:
                log_exception("Could not load thumbnail index.")
    
    def _saveIndex(self):
        if self.good and self.settings != None:
            try:
                self.settings.setValue("categoryPictures", self.categoryPictures)
                
                thumbnailDict = {}
                for i in range(self.categoryModel.rowCount()):
                    item = self.categoryModel.item(i)
                    cat = item.data(Qt.DisplayRole).toString()
                    path = item.data(CategoriesModel.PATH_ROLE)
                    thumbnailDict[cat] = path
                self.settings.setValue("categoryThumbnails", thumbnailDict)
            except:
                log_exception("Could not save thumbnail index.")
    
    def _picturesDirectory(self):
        return os.path.join(get_settings().get_main_config_dir(), "remote_pictures")
        
    def _fileForThumbnail(self, url, _category):
        path = urlparse.urlparse(url).path
        oldSuffix = os.path.splitext(path)[1]
        return tempfile.NamedTemporaryFile(suffix=oldSuffix, dir=self._picturesDirectory(), delete=False)
    
    def _getThumbnailSize(self):
        return self.THUMBNAIL_SIZE
    
    def _createThumbnail(self, path, url, category):#
        if not os.path.exists(path):
            raise IOError("File '%s' does not exist." % path)
        
        outFile = self._fileForThumbnail(url, category)
        fileName = outFile.name
        
        oldPixmap = QPixmap.fromImage(QImage(path))
        newPixmap = oldPixmap.scaled(self._getThumbnailSize(),self._getThumbnailSize(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
        newPixmap.save(fileName, format='jpeg')
        return fileName
            
    def _addCategory(self, category, thumbnailPath = None, firstImagePath = None, firstImageURL = None):
        # cache category image
        if thumbnailPath != None:
            self.categoryModel.addCategory(category, thumbnailPath)
        elif firstImagePath != None:
            if firstImageURL == None:
                raise Exception("URL must not be None.")
            self.categoryModel.addCategory(category, self._createThumbnail(firstImagePath, firstImageURL, category))
        else:
            raise Exception("No image path specified.")
        self.categoryPictures[category] = []


    def addPicture(self, path, url, category):
        if not category in self.categoryPictures:
            self._addCategory(category, firstImagePath=path, firstImageURL=url)
        self.categoryPictures[category].append(url)
        
    def destroyWidget(self):
        self._saveIndex()

class CategoriesModel(QStandardItemModel):
    SORT_ROLE = Qt.UserRole + 1
    PATH_ROLE = SORT_ROLE + 1
    
    def __init__(self):
        super(CategoriesModel, self).__init__()
        self.setColumnCount(1)
        
    def addCategory(self, cat, firstImage):
        item = QStandardItem()
        item.setData(QVariant(cat), Qt.DisplayRole)
        item.setData(QVariant(QIcon(firstImage)), Qt.DecorationRole)
        item.setData(QVariant(firstImage), self.PATH_ROLE)
        self.appendRow([item])

if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : RemotePicturesGui(window))