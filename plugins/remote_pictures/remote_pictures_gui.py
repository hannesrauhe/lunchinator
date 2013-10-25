import sys
from lunchinator import log_exception, get_settings, convert_string, log_debug
from PyQt4.QtGui import QImage, QPixmap, QStackedWidget, QIcon, QListView, QStandardItemModel, QStandardItem, QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QLabel, QFont, QColor, QSizePolicy
from PyQt4.QtCore import QTimer, QSize, Qt, QVariant, QSettings, pyqtSlot, QModelIndex
from lunchinator.resizing_image_label import ResizingWebImageLabel
import tempfile
import os
import urlparse
from functools import partial

class RemotePicturesGui(QStackedWidget):
    THUMBNAIL_SIZE = 200
    
    def __init__(self,parent):
        super(RemotePicturesGui, self).__init__(parent)
        
        self.good = True
        self.settings = None
        self.categoryPictures = {}
        self.currentCategory = None
        self.currentIndex = 0

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
        self.categoryView.doubleClicked.connect(self._itemDoubleClicked)

        self.addWidget(self.categoryView)
        
        self.imageLabel = ResizingWebImageLabel(self, True)
        imageViewerLayout = QVBoxLayout(self.imageLabel)
        imageViewerLayout.setContentsMargins(0, 0, 0, 0)
        imageViewerLayout.setSpacing(0)
        
        topWidget = HiddenWidget(self.imageLabel)
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        backButton = QToolButton(topWidget)
        backButton.setArrowType(Qt.LeftArrow)
        backButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        backButton.setText("Categories")
        topLayout.addWidget(backButton, 0, Qt.AlignLeft)
        imageViewerLayout.addWidget(topWidget, 0)
        
        navButtonsWidget = QWidget(self.imageLabel)
        navButtonsLayout = QHBoxLayout(navButtonsWidget)
        navButtonsLayout.setContentsMargins(0, 0, 0, 0)
        
        self.prevButton = HiddenToolButton(self.imageLabel)
        self.prevButton.setArrowType(Qt.LeftArrow)
        self.prevButton.setEnabled(False)
        self.prevButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        navButtonsLayout.addWidget(self.prevButton, 0, Qt.AlignLeft)
        
        self.nextButton = HiddenToolButton(self.imageLabel)
        self.nextButton.setArrowType(Qt.RightArrow)
        self.nextButton.setEnabled(False)
        self.nextButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        navButtonsLayout.addWidget(self.nextButton, 0, Qt.AlignRight)
        
        imageViewerLayout.addWidget(navButtonsWidget, 1)
        
        self.descriptionLabel = HiddenLabel("This is how I test a QLabel", self.imageLabel)
        self.descriptionLabel.setWordWrap(True)
        self.descriptionLabel.setAutoFillBackground(True)
        self.descriptionLabel.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        oldFont = self.descriptionLabel.font()
        self.descriptionLabel.setFont(QFont(oldFont.family(), 14))
        self.descriptionLabel.setMargin(5)
        self.descriptionLabel.setAlignment(Qt.AlignCenter)
        palette = self.descriptionLabel.palette()
        palette.setColor(self.descriptionLabel.backgroundRole(), QColor(0,0,0,200))
        palette.setColor(self.descriptionLabel.foregroundRole(), Qt.white)
        self.descriptionLabel.setPalette(palette)
        imageViewerLayout.addWidget(self.descriptionLabel, 0)
                
        self.addWidget(self.imageLabel)
        
        self.nextButton.clicked.connect(self._displayNextImage)
        self.prevButton.clicked.connect(self._displayPreviousImage)
        backButton.clicked.connect(partial(self.setCurrentIndex, 0))
                
        # load categories index
        self._loadIndex()
        
    @pyqtSlot(QModelIndex)
    def _itemDoubleClicked(self, index):
        item = self.categoryModel.item(index.row())
        self._openCategory(convert_string(item.data(Qt.DisplayRole).toString()))
        
    def _displayImage(self, index = -1):
        if self.currentCategory == None:
            return
        
        if index < 0:
            index = len(self.categoryPictures[self.currentCategory]) + index
            
        if index < 0 or index >= len(self.categoryPictures[self.currentCategory]):
            # invalid index
            return
        
        self.currentIndex = index
        newestPicTuple = self.categoryPictures[self.currentCategory][self.currentIndex]
        self.imageLabel.setURL(newestPicTuple[0])
        self.setCurrentIndex(1)
        
        self.prevButton.setEnabled(self.currentIndex > 0)
        self.nextButton.setEnabled(self.currentIndex < len(self.categoryPictures[self.currentCategory]) - 1)
        
    def _displayNextImage(self):
        self._displayImage(self.currentIndex + 1)
        
    def _displayPreviousImage(self):
        self._displayImage(self.currentIndex - 1)    
    
    def _openCategory(self, cat):
        self.currentCategory = cat
        self._displayImage()
        
    def _loadIndex(self):
        if self.good:
            try:
                self.settings = QSettings(os.path.join(self._picturesDirectory(), u"index"), QSettings.NativeFormat)
                storedThumbnails  = self.settings.value("categoryThumbnails", None)
                if storedThumbnails != None:
                    storedThumbnails = storedThumbnails.toMap()
                    for aCat in storedThumbnails:
                        self._addCategory(convert_string(aCat), thumbnailPath=convert_string(storedThumbnails[aCat].toString()))
                        
                storedCategories = self.settings.value("categoryPictures", None)
                if storedCategories != None:
                    tmpDict = storedCategories.toMap()
                    self.categoryPictures = {}
                    for aCat in tmpDict:
                        newKey = convert_string(aCat)
                        picTupleList = tmpDict[aCat].toList()
                        newTupleList = []
                        for picTuple in picTupleList:
                            tupleList = picTuple.toList()
                            newTupleList.append([convert_string(tupleList[0].toString()), convert_string(tupleList[1].toString())])
                        self.categoryPictures[newKey] = newTupleList
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

    def addPicture(self, path, url, category, description):
        if not category in self.categoryPictures:
            self._addCategory(category, firstImagePath=path, firstImageURL=url)
        self.categoryPictures[category].append([url, description])
        
    def destroyWidget(self):
        self._saveIndex()
        
class HiddenWidgetBase(object):
    INITIAL_TIMEOUT = 2000
    NUM_STEPS = 15
    INTERVAL = 20
    
    def __init__(self, minOpacity = 0.1, maxOpacity = 0.8):
        # TODO option for min / max opacity
        self.good = False
        self.fadingEnabled = False
        try:
            from PyQt4.QtGui import QGraphicsOpacityEffect
            self.minOpacity = minOpacity
            self.maxOpacity = maxOpacity
            self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
            
            self.fadeIn = False
            self.effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.effect)
            self.effect.setOpacity(self.maxOpacity)
            
            self.good = True
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._fade)
            QTimer.singleShot(self.INITIAL_TIMEOUT, self._fadeOut)
        except:
            log_debug(u"Could not enable opacity effects. %s: %s" % (sys.exc_info()[0].__name__, unicode(sys.exc_info()[1])))
        
    def _fadeOut(self):
        self.fadingEnabled = True
        self.timer.start(self.INTERVAL * 1.5)
    
    def _fade(self):
        if self.fadeIn:
            opacity = self.effect.opacity() + self.incr
            self.effect.setOpacity(opacity)
            return opacity < self.maxOpacity
        else:
            opacity = self.effect.opacity() - self.incr
            self.effect.setOpacity(opacity)
            return opacity > self.minOpacity
        
    def _mouseEntered(self):
        if self.good and self.fadingEnabled:
            self.fadeIn = True
            self.timer.start(self.INTERVAL)
        
    def _mouseLeft(self):
        if self.good and self.fadingEnabled:
            self.fadeIn = False
            self.timer.start(self.INTERVAL)
        
class HiddenLabel(QLabel, HiddenWidgetBase):
    def __init__(self, parent, text = None):
        QLabel.__init__(self, parent, text)
        HiddenWidgetBase.__init__(self, maxOpacity=1)
    
    def enterEvent(self, event):
        self._mouseEntered()
        return super(HiddenLabel, self).enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouseLeft()
        return super(HiddenLabel, self).leaveEvent(event)

class HiddenWidget(QWidget, HiddenWidgetBase):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        HiddenWidgetBase.__init__(self)
        
    def enterEvent(self, event):
        self._mouseEntered()
        return super(HiddenWidget, self).enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouseLeft()
        return super(HiddenWidget, self).leaveEvent(event)

class HiddenToolButton(QToolButton, HiddenWidgetBase):
    def __init__(self, parent):
        QToolButton.__init__(self, parent)
        HiddenWidgetBase.__init__(self)
        
    def enterEvent(self, event):
        self._mouseEntered()
        return super(HiddenToolButton, self).enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouseLeft()
        return super(HiddenToolButton, self).leaveEvent(event)

class CategoriesModel(QStandardItemModel):
    SORT_ROLE = Qt.UserRole + 1
    PATH_ROLE = SORT_ROLE + 1
    
    def __init__(self):
        super(CategoriesModel, self).__init__()
        self.setColumnCount(1)
        
    def addCategory(self, cat, firstImage):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(cat), Qt.DisplayRole)
        item.setData(QVariant(QIcon(firstImage)), Qt.DecorationRole)
        item.setData(QVariant(firstImage), self.PATH_ROLE)
        self.appendRow([item])

if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : RemotePicturesGui(window))