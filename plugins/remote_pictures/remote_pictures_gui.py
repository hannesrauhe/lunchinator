import sys
from lunchinator import log_exception, get_settings, convert_string, log_debug
from PyQt4.QtGui import QImage, QPixmap, QStackedWidget, QIcon, QListView, QStandardItemModel, QStandardItem, QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QLabel, QFont, QColor, QSizePolicy, QSortFilterProxyModel,\
    QFrame
from PyQt4.QtCore import QTimer, QSize, Qt, QVariant, QSettings, pyqtSlot, pyqtSignal, QModelIndex
from lunchinator.resizing_image_label import ResizingWebImageLabel
import tempfile
import os
from functools import partial
from lunchinator.callables import AsyncCall

class RemotePicturesGui(QStackedWidget):
    MIN_THUMBNAIL_SIZE = 16
    MAX_THUMBNAIL_SIZE = 1024
    UNCATEGORIZED = "Not Categorized"
    
    categoryOpened = pyqtSignal()
    minOpacityChanged = pyqtSignal(float)
    maxOpacityChanged = pyqtSignal(float)
    
    def __init__(self,parent,rp):
        super(RemotePicturesGui, self).__init__(parent)
        
        self.rp = rp
        self.good = True
        self.settings = None
        self.categoryPictures = {}
        self.currentCategory = None
        self.curPicIndex = 0

        if not os.path.exists(self._picturesDirectory()):
            try:
                os.makedirs(self._picturesDirectory())
            except:
                log_exception("Could not create remote pictures directory '%s'" % self._picturesDirectory())
                self.good = False
                
        self.categoryModel = CategoriesModel()
        self.sortProxy = QSortFilterProxyModel(self)
        self.sortProxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.sortProxy.setSortRole(CategoriesModel.SORT_ROLE)
        self.sortProxy.setDynamicSortFilter(True)
        self.sortProxy.setSourceModel(self.categoryModel)
        self.sortProxy.sort(0)
        
        self.categoryView = QListView(self)
        self.categoryView.setModel(self.sortProxy)
        self.categoryView.setViewMode(QListView.IconMode);
        self.categoryView.setIconSize(QSize(200,200));
        self.categoryView.setResizeMode(QListView.Adjust);
        self.categoryView.doubleClicked.connect(self._itemDoubleClicked)
        self.categoryView.setFrameShape(QFrame.NoFrame)

        self.addWidget(self.categoryView)
        
        self.imageLabel = ResizingWebImageLabel(self, smooth_scaling=self.rp.options['smooth_scaling'])
        imageViewerLayout = QVBoxLayout(self.imageLabel)
        imageViewerLayout.setContentsMargins(0, 0, 0, 0)
        imageViewerLayout.setSpacing(0)
        
        defaultFont = self.font()
        self.categoryLabel = HiddenLabel(self.imageLabel, fontSize=16, fontOptions=QFont.Bold)
        topLayout = QHBoxLayout(self.categoryLabel)
        topLayout.setContentsMargins(0, 0, 0, 0)
        backButton = QToolButton(self.categoryLabel)
        backButton.setFont(QFont(defaultFont.family(), defaultFont.pointSize(), 0))
        backButton.setFocusPolicy(Qt.NoFocus)
        backButton.setArrowType(Qt.LeftArrow)
        backButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        backButton.setText("Categories")
        topLayout.addWidget(backButton, 0, Qt.AlignLeft)
        imageViewerLayout.addWidget(self.categoryLabel, 0)
        
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
        
        self.descriptionLabel = HiddenLabel(self.imageLabel, fontSize=14)
        self.descriptionLabel.setWordWrap(True)
        imageViewerLayout.addWidget(self.descriptionLabel, 0)
                
        self.addWidget(self.imageLabel)
        
        self.nextButton.clicked.connect(self._displayNextImage)
        self.prevButton.clicked.connect(self._displayPreviousImage)
        backButton.clicked.connect(partial(self.setCurrentIndex, 0))
        self._initializeHiddenWidget(self.categoryLabel)
        self._initializeHiddenWidget(self.prevButton)
        self._initializeHiddenWidget(self.nextButton)
        self._initializeHiddenWidget(self.descriptionLabel)
        
        self.minOpacityChanged.emit(float(self.rp.options['min_opacity']) / 100.)
        self.maxOpacityChanged.emit(float(self.rp.options['max_opacity']) / 100.)
                
        self._createThumbnailAndAddCategory = AsyncCall(self,
                                                        self._createThumbnail,
                                                        self._addCategoryAndCloseFile)
                
        # load categories index
        self._loadIndex()
        
    def hasPicture(self, url, cat):
        if not cat:
            cat = self.UNCATEGORIZED
        if not cat in self.categoryPictures:
            return False
        for anUrl, _desc in self.categoryPictures[cat]:
            if url == anUrl:
                return True
        return False
    
    def getCategories(self):
        return sorted(self.categoryPictures.keys(), key=lambda cat : cat.lower() if cat != RemotePicturesGui.UNCATEGORIZED else "")
        
    def _initializeHiddenWidget(self, w):
        self.categoryOpened.connect(w.showTemporarily)
        self.minOpacityChanged.connect(w.setMinOpacity)
        self.maxOpacityChanged.connect(w.setMaxOpacity)

    @pyqtSlot(QModelIndex)
    def _itemDoubleClicked(self, index):
        index = self.sortProxy.mapToSource(index)
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
        
        self.curPicIndex = index
        newestPicTuple = self.categoryPictures[self.currentCategory][self.curPicIndex]
        self.imageLabel.setURL(newestPicTuple[0])
        self.descriptionLabel.setText(newestPicTuple[1])
        self.setCurrentIndex(1)
        
        self.prevButton.setEnabled(self.curPicIndex > 0)
        self.nextButton.setEnabled(self.curPicIndex < len(self.categoryPictures[self.currentCategory]) - 1)
        
    def _displayNextImage(self):
        self._displayImage(self.curPicIndex + 1)
        
    def _displayPreviousImage(self):
        self._displayImage(self.curPicIndex - 1)    
    
    def _openCategory(self, cat):
        self.currentCategory = cat
        self.categoryLabel.setText(cat)
        self._displayImage()
        self.categoryOpened.emit()
        
    def _loadIndex(self):
        if self.good:
            try:
                self.settings = QSettings(os.path.join(self._picturesDirectory(), u"index"), QSettings.NativeFormat)
                        
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
                        if len(newTupleList) > 0:
                            self.categoryPictures[newKey] = newTupleList
                            
                storedThumbnails  = self.settings.value("categoryThumbnails", None)
                if storedThumbnails != None:
                    storedThumbnails = storedThumbnails.toMap()
                    for aCat in storedThumbnails:
                        thumbnailPath = convert_string(storedThumbnails[aCat].toString())
                        aCat = convert_string(aCat)
                        if aCat in self.categoryPictures:
                            self._addCategory(aCat, thumbnailPath=thumbnailPath)
                        else:
                            # there has been an error, the category is empty. Remove it.
                            if os.path.exists(thumbnailPath):
                                os.remove(thumbnailPath)
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
                self.settings.sync()
            except:
                log_exception("Could not save thumbnail index.")
    
    def _picturesDirectory(self):
        return os.path.join(get_settings().get_main_config_dir(), "remote_pictures")
        
    def _fileForThumbnail(self, _category):
        return tempfile.NamedTemporaryFile(suffix='.jpg', dir=self._picturesDirectory(), delete=False)
    
    def thumbnailSizeChanged(self, newValue):
        self.categoryModel.thumbnailSizeChanged(newValue)
    
    def _getThumbnailSize(self):
        return self.rp.options['thumbnail_size']
    
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
        self.categoryModel.addCategory(category, thumbnailPath, self._getThumbnailSize())
        imageFile.close()
            
    def _addCategory(self, category, thumbnailPath = None, imageFile = None):
        # cache category image
        closeImmediately = True
        try:
            if thumbnailPath != None:
                self.categoryModel.addCategory(category, thumbnailPath, self._getThumbnailSize())
            elif imageFile != None:
                # create thumbnail asynchronously, then close imageFile
                self._createThumbnailAndAddCategory(imageFile, category)
                closeImmediately = False
            else:
                raise Exception("No image path specified.")
            if category not in self.categoryPictures:
                self.categoryPictures[category] = []
        finally:
            if closeImmediately and imageFile != None:
                imageFile.close()

    def addPicture(self, imageFile, url, category, description):
        if category == None:
            category = self.UNCATEGORIZED
        if not category in self.categoryPictures:
            self._addCategory(category, imageFile = imageFile)
            self.rp.privacySettingsChanged()
        
        self.categoryPictures[category].append([url, description if description != None else u""])
        if self.currentIndex() == 1 and category == self.currentCategory:
            # if category is open, display image immediately
            self._displayImage()
        
    def destroyWidget(self):
        self._saveIndex()
        
class HiddenWidgetBase(object):
    INITIAL_TIMEOUT = 2000
    NUM_STEPS = 15
    INTERVAL = 20
    
    def __init__(self):
        self.good = False
        self.fadingEnabled = False
        self.minOpacity = 0.
        self.maxOpacity = 1.
        self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
        self.fadeIn = False
        try:
            from PyQt4.QtGui import QGraphicsOpacityEffect
            
            self.effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.effect)
            
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._fade)
            self.good = True
        except:
            log_debug(u"Could not enable opacity effects. %s: %s" % (sys.exc_info()[0].__name__, unicode(sys.exc_info()[1])))
        
    def setMinOpacity(self, newVal):
        self.minOpacity = newVal
        self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
        if self.fadingEnabled and not self.timer.isActive():
            self.timer.start(self.INTERVAL)
    
    def setMaxOpacity(self, newVal):
        self.maxOpacity = newVal
        self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
        if self.fadingEnabled and not self.timer.isActive():
            self.timer.start(self.INTERVAL)
        
    def showTemporarily(self):
        if self.good:
            self.fadingEnabled = False
            self.fadeIn = False
            self.timer.stop()
            self.effect.setOpacity(self.maxOpacity)
            QTimer.singleShot(self.INITIAL_TIMEOUT, self._fadeOut)
        
    def _fadeOut(self):
        self.fadingEnabled = True
        self.timer.start(self.INTERVAL * 1.5)
    
    def _fade(self):
        if self.fadeIn:
            desOp = self.maxOpacity
        else:
            desOp = self.minOpacity
        
        opacity = self.effect.opacity()
        if abs(opacity - desOp) < self.incr:
            # prevent flickering if timer does not stop immediately
            return
        
        if opacity < desOp:
            opacity += self.incr
            self.effect.setOpacity(opacity)
        else:
            opacity -= self.incr
            self.effect.setOpacity(opacity)
        
        #finish animation if desired opacity is reached
        if abs(opacity - desOp) < self.incr:
            self.timer.stop()
        
    def _mouseEntered(self):
        if self.good and self.fadingEnabled:
            self.fadeIn = True
            self.timer.start(self.INTERVAL)
        
    def _mouseLeft(self):
        if self.good and self.fadingEnabled:
            self.fadeIn = False
            self.timer.start(self.INTERVAL)
        
class HiddenLabel(QLabel, HiddenWidgetBase):
    def __init__(self, parent, fontSize = 14, fontOptions = 0):
        QLabel.__init__(self, parent)
        HiddenWidgetBase.__init__(self)
        
        self.setAutoFillBackground(True)
        oldFont = self.font()
        self.setFont(QFont(oldFont.family(), fontSize, fontOptions))
        self.setMargin(5)
        self.setAlignment(Qt.AlignCenter)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(0,0,0,200))
        palette.setColor(self.foregroundRole(), Qt.white)
        self.setPalette(palette)
    
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
        self.setFocusPolicy(Qt.NoFocus)
        
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
        
    def _createThumbnail(self, imagePath, thumbnailSize):
        """Called asynchronously, hence, no QPixmaps here."""
        image = QImage(imagePath)
        return image.scaled(QSize(thumbnailSize, thumbnailSize), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
    def _setThumbnail(self, item, image):
        item.setData(QVariant(QIcon(QPixmap.fromImage(image))), Qt.DecorationRole)
        
    def _initializeItem(self, item, imagePath, thumbnailSize):
        AsyncCall(self, self._createThumbnail, partial(self._setThumbnail, item))(imagePath, thumbnailSize)
        
    def addCategory(self, cat, firstImage, thumbnailSize):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(cat), Qt.DisplayRole)
        self._initializeItem(item, firstImage, thumbnailSize)
        item.setData(QVariant(firstImage), self.PATH_ROLE)
        item.setData(QVariant(cat if cat != RemotePicturesGui.UNCATEGORIZED else ""), self.SORT_ROLE)
        self.appendRow([item])
        
    def thumbnailSizeChanged(self, thumbnailSize):
        for i in range(self.rowCount()):
            item = self.item(i)
            self._initializeItem(item, item.data(self.PATH_ROLE).toString(), thumbnailSize)

if __name__ == '__main__':
    class RemotePicturesWrapper(object):
        options = {u'min_opacity': 10,
                   u'max_opacity': 90,
                   u'thumbnail_size': 200,
                   u'smooth_scaling':True}
    
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : RemotePicturesGui(window, RemotePicturesWrapper()))