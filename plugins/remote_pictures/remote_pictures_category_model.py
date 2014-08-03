from PyQt4.QtGui import QStandardItemModel, QImage, QIcon, QPixmap,\
    QStandardItem
from PyQt4.QtCore import Qt, QSize, QVariant, pyqtSignal
from lunchinator.callables import AsyncCall
from functools import partial
from remote_pictures.remote_pictures_storage import RemotePicturesStorage
from lunchinator import convert_string
import os

class CategoriesModel(QStandardItemModel):
    SORT_ROLE = Qt.UserRole + 1
    PATH_ROLE = SORT_ROLE + 1
    
    MIN_THUMBNAIL_SIZE = 16
    MAX_THUMBNAIL_SIZE = 1024
    
    categoriesChanged = pyqtSignal()
    
    def __init__(self):
        super(CategoriesModel, self).__init__()
        self.setColumnCount(1)
        self._categoryIcons = {}
        
    def _createThumbnail(self, imagePath, thumbnailSize, adding):
        """Called asynchronously, hence, no QPixmaps here."""
        image = QImage(imagePath)
        return image.scaled(QSize(thumbnailSize, thumbnailSize), Qt.KeepAspectRatio, Qt.SmoothTransformation), adding
        
    def _setThumbnail(self, item, cat, aTuple):
        image, adding = aTuple
        icon = QIcon(QPixmap.fromImage(image))
        item.setData(QVariant(icon), Qt.DecorationRole)
        self._categoryIcons[cat] = icon
        if adding:
            self.categoriesChanged.emit()
        
    def _initializeItem(self, item, imagePath, thumbnailSize, cat, adding):
        if imagePath and os.path.exists(imagePath):
            AsyncCall(self, self._createThumbnail, partial(self._setThumbnail, item, cat))(imagePath, thumbnailSize, adding)
        elif adding:
            self.categoriesChanged.emit()
        
    def getCategoryIcon(self, cat):
        if cat in self._categoryIcons:
            return self._categoryIcons[cat]
        return None
        
    def addCategory(self, cat, thumbnailPath, thumbnailSize):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(cat), Qt.DisplayRole)
        self._initializeItem(item, thumbnailPath, thumbnailSize, cat, True)
        item.setData(QVariant() if thumbnailPath is None else QVariant(thumbnailPath), self.PATH_ROLE)
        item.setData(QVariant(cat if cat != RemotePicturesStorage.UNCATEGORIZED else ""), self.SORT_ROLE)
        self.appendRow([item])
        
    def thumbnailSizeChanged(self, thumbnailSize):
        for i in range(self.rowCount()):
            item = self.item(i)
            cat = convert_string(item.data(Qt.DisplayRole).toString())
            self._initializeItem(item, item.data(self.PATH_ROLE).toString(), thumbnailSize, cat, False)
            