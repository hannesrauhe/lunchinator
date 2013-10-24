import urllib2, sys, shutil
from lunchinator import log_exception
from PyQt4.QtGui import QImage, QPixmap, QStackedWidget, QIcon, QListView, QStandardItemModel, QStandardItem
from PyQt4.QtCore import QTimer, QSize, Qt, QVariant
from lunchinator.resizing_image_label import ResizingImageLabel
import tempfile

class RemotePicturesGui(QStackedWidget):
    def __init__(self,parent):
        super(RemotePicturesGui, self).__init__(parent)
        
        self.categoryPictures = {}
        
        self.categoryModel = CategoriesModel()
        
        self.categoryView = QListView(self)
        self.categoryView.setModel(self.categoryModel)
        self.categoryView.setViewMode(QListView.IconMode);
        self.categoryView.setIconSize(QSize(200,200));
        self.categoryView.setResizeMode(QListView.Adjust);
        
        self.addPicture("/home/corny/Bilder/No..jpg", "anUrl", "Category 1")
        #self.categoryModel.addCategory("Category 2", "/home/corny/Bilder/Okay.png")
        
        self.addWidget(self.categoryView)
        
    def addPicture(self, path, url, category):
        if not category in self.categoryPictures:
            self._addCategory(category, path)
        self.categoryPictures[category].append(url)
            
    def _addCategory(self, category, firstImagePath):
        # cache category image
        tmpFile = tempfile.NamedTemporaryFile(delete=False)
        with open(firstImagePath, 'rb') as inFile:
            shutil.copyfileobj(inFile, tmpFile)
        self.categoryModel.addCategory(category, tmpFile.name)
        tmpFile.close()
        self.categoryPictures[category] = []

class CategoriesModel(QStandardItemModel):
    SORT_ROLE = Qt.UserRole + 1
    
    def __init__(self):
        super(CategoriesModel, self).__init__()
        self.setColumnCount(1)
        
    def addCategory(self, cat, firstImage):
        item = QStandardItem()
        item.setData(QVariant(cat), Qt.DisplayRole)
        item.setData(QVariant(QIcon(firstImage)), Qt.DecorationRole)
        self.appendRow([item])

if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : RemotePicturesGui(window))