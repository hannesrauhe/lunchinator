from remote_pictures.remote_pictures_storage import RemotePicturesStorage
from remote_pictures.remote_pictures_category_model import CategoriesModel
from lunchinator import convert_string, get_peers
from lunchinator.gui_elements import ResizingWebImageLabel
from lunchinator.utilities import formatTime
from lunchinator.log.logging_func import loggingFunc
from lunchinator.log.logging_slot import loggingSlot

from PyQt4.QtGui import QStackedWidget, QListView, QWidget, QHBoxLayout, \
    QVBoxLayout, QToolButton, QLabel, QFont, QColor, QSizePolicy, QSortFilterProxyModel, \
    QFrame, QMenu, QCursor, QImage
from PyQt4.QtCore import QTimer, QSize, Qt, pyqtSignal, QModelIndex, QPoint

import sys, os
from functools import partial
from time import localtime

class RemotePicturesGui(QStackedWidget):
    openCategory = pyqtSignal(object) # category
    displayNext = pyqtSignal(object, int) # current category, current ID
    displayPrev = pyqtSignal(object, int) # current category, current ID
    pictureDownloaded = pyqtSignal(object, object, object) # current category, url, pic data
    
    minOpacityChanged = pyqtSignal(float)
    maxOpacityChanged = pyqtSignal(float)
    
    setCategoryThumbnail = pyqtSignal(object, QImage) # category, thumbnail pixmap
    
    _categoryOpened = pyqtSignal() # used to flash hidden widgets
    
    def __init__(self, parent, logger, smoothScaling, minOpacity, maxOpacity):
        super(RemotePicturesGui, self).__init__(parent)
        
        self.logger = logger
        self.good = True
        self.settings = None
        self.categoryPictures = {}
        self.currentCategory = None
        self.curPicIndex = 0
        self.categoryModel = CategoriesModel(logger)
        self.sortProxy = None
        
        self.categoryView = QListView(self)
        self.categoryView.setViewMode(QListView.IconMode);
        self.categoryView.setIconSize(QSize(200,200));
        self.categoryView.setResizeMode(QListView.Adjust);
        self.categoryView.doubleClicked.connect(self._itemDoubleClicked)
        self.categoryView.setFrameShape(QFrame.NoFrame)
        
        self.sortProxy = QSortFilterProxyModel(self)
        self.sortProxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.sortProxy.setSortRole(CategoriesModel.SORT_ROLE)
        self.sortProxy.setDynamicSortFilter(True)
        self.sortProxy.setSourceModel(self.categoryModel)
        self.sortProxy.sort(0)
        self.categoryView.setModel(self.sortProxy)

        self.addWidget(self.categoryView)
        
        self.imageLabel = ResizingWebImageLabel(self, self.logger, smooth_scaling=smoothScaling)
        self.imageLabel.imageDownloaded.connect(self.pictureDownloadedSlot)
        self.imageLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.imageLabel.customContextMenuRequested.connect(self._showImageContextMenu)
        imageViewerLayout = QVBoxLayout(self.imageLabel)
        imageViewerLayout.setContentsMargins(0, 0, 0, 0)
        imageViewerLayout.setSpacing(0)
        
        defaultFont = self.font()
        self.categoryLabel = HiddenLabel(self.imageLabel, self.logger, fontSize=16, fontOptions=QFont.Bold)
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
        
        self.prevButton = HiddenToolButton(self.imageLabel, self.logger)
        self.prevButton.setArrowType(Qt.LeftArrow)
        self.prevButton.setEnabled(False)
        self.prevButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        navButtonsLayout.addWidget(self.prevButton, 0, Qt.AlignLeft)
        
        self.nextButton = HiddenToolButton(self.imageLabel, self.logger)
        self.nextButton.setArrowType(Qt.RightArrow)
        self.nextButton.setEnabled(False)
        self.nextButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        navButtonsLayout.addWidget(self.nextButton, 0, Qt.AlignRight)
        
        imageViewerLayout.addWidget(navButtonsWidget, 1)
        
        self.descriptionLabel = HiddenLabel(self.imageLabel, self.logger, fontSize=14)
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
        
        self.minOpacityChanged.emit(float(minOpacity) / 100.)
        self.maxOpacityChanged.emit(float(maxOpacity) / 100.)
    
    def getCategoryIcon(self, cat):
        return self.categoryModel.getCategoryIcon(cat)
        
    @loggingSlot(QPoint)
    def _showImageContextMenu(self, _point):
        pixmap = self.imageLabel.getRawPixmap()
        if pixmap is None or pixmap.isNull():
            return
        m = QMenu()
        m.addAction(u"Set as category thumbnail", self._setCurrentPictureAsThumbnail)
        m.exec_(QCursor.pos())
        m.deleteLater()
        
    @loggingSlot()
    def _setCurrentPictureAsThumbnail(self):
        if self.currentCategory is None:
            self.logger.error("Current category is None")
            return
        pixmap = self.imageLabel.getRawPixmap()
        if pixmap is None or pixmap.isNull():
            self.logger.error("NULL pixmap")
            return
        image = pixmap.toImage()
        if image.isNull():
            self.logger.error("Error converting pixmap to image")
            return
        self.setCategoryThumbnail.emit(self.currentCategory, image)
        
    def _initializeHiddenWidget(self, w):
        self._categoryOpened.connect(w.showTemporarily)
        self.minOpacityChanged.connect(w.setMinOpacity)
        self.maxOpacityChanged.connect(w.setMaxOpacity)

    @loggingSlot(QModelIndex)
    def _itemDoubleClicked(self, index):
        index = self.sortProxy.mapToSource(index)
        item = self.categoryModel.item(index.row())
        cat = item.data(CategoriesModel.CAT_ROLE).toString()
        self.openCategory.emit(cat)
        
    def _deactivateButtons(self):
        self.nextButton.setEnabled(False)
        self.prevButton.setEnabled(False)
        
    @loggingSlot()
    def _displayNextImage(self):
        self._deactivateButtons()
        self.displayNext.emit(self.currentCategory, self.curPicIndex)
    
    @loggingSlot()
    def _displayPreviousImage(self):
        self._deactivateButtons()
        self.displayPrev.emit(self.currentCategory, self.curPicIndex)
    
    @loggingSlot(object, int, list, bool, bool)
    def displayImage(self, cat, picID, picRow, hasPrev, hasNext):
        cat = convert_string(cat)
        picURL = convert_string(picRow[RemotePicturesStorage.PIC_URL_COL])
        picFile = convert_string(picRow[RemotePicturesStorage.PIC_FILE_COL])
        picDesc = convert_string(picRow[RemotePicturesStorage.PIC_DESC_COL])
        if picDesc is None:
            picDesc = u""
        picSender = convert_string(picRow[RemotePicturesStorage.PIC_SENDER_COL])
        picTime = picRow[RemotePicturesStorage.PIC_ADDED_COL]
        
        self.currentCategory = cat
        self.categoryLabel.setText(cat)
        
        self.curPicIndex = picID
        if picFile and os.path.exists(picFile):
            self.imageLabel.setImage(picFile)
        elif picURL:
            self.imageLabel.setURL(picURL)
        else:
            self.logger.warning("No image source specified")
            self.imageLabel.displayFallbackPic()
        
        if picSender:
            self.imageLabel.setToolTip(u"Sent to you by %s,\nSent %s" % (get_peers().getDisplayedPeerName(pID=picSender),
                                                                         formatTime(localtime(picTime))))
        else:
            self.imageLabel.setToolTip(u"")
            
        self.descriptionLabel.setText(picDesc)
        self.setCurrentIndex(1)
        
        self.prevButton.setEnabled(hasPrev)
        self.nextButton.setEnabled(hasNext)
        
        self._categoryOpened.emit()
    
    def thumbnailSizeChanged(self, newValue):
        self.categoryModel.thumbnailSizeChanged(newValue)
        
    def setSmoothScaling(self, newValue):
        self.imageLabel.setSmoothScaling(newValue)
        
    def isShowingCategory(self, category):
        return self.currentIndex() == 1 and category == self.currentCategory
        
    def destroyWidget(self):
        pass
    
    @loggingSlot(object, object)
    def pictureDownloadedSlot(self, url, picData):
        if self.currentCategory is not None:
            self.pictureDownloaded.emit(self.currentCategory, url, picData)
        
class HiddenWidgetBase(object):
    INITIAL_TIMEOUT = 2000
    NUM_STEPS = 15
    INTERVAL = 20
    
    def __init__(self, logger):
        self.logger = logger
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
            self.logger.debug(u"Could not enable opacity effects. %s: %s", sys.exc_info()[0].__name__, unicode(sys.exc_info()[1]))
        
    # cannot use loggingSlot here because this is no QObject
    @loggingFunc
    def setMinOpacity(self, newVal):
        self.minOpacity = newVal
        self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
        if self.fadingEnabled and not self.timer.isActive():
            self.timer.start(self.INTERVAL)
    
    # cannot use loggingSlot here because this is no QObject
    @loggingFunc
    def setMaxOpacity(self, newVal):
        self.maxOpacity = newVal
        self.incr = (self.maxOpacity - self.minOpacity) / self.NUM_STEPS
        if self.fadingEnabled and not self.timer.isActive():
            self.timer.start(self.INTERVAL)
        
    # cannot use loggingSlot here because this is no QObject
    @loggingFunc
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
    
    # cannot use loggingSlot here because this is no QObject
    @loggingFunc
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
    def __init__(self, parent, logger, fontSize = 14, fontOptions = 0):
        QLabel.__init__(self, parent)
        HiddenWidgetBase.__init__(self, logger)
        
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
    def __init__(self, parent, logger):
        QWidget.__init__(self, parent)
        HiddenWidgetBase.__init__(self, logger)
        
    def enterEvent(self, event):
        self._mouseEntered()
        return super(HiddenWidget, self).enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouseLeft()
        return super(HiddenWidget, self).leaveEvent(event)

class HiddenToolButton(QToolButton, HiddenWidgetBase):
    def __init__(self, parent, logger):
        QToolButton.__init__(self, parent)
        HiddenWidgetBase.__init__(self, logger)
        self.setFocusPolicy(Qt.NoFocus)
        
    def enterEvent(self, event):
        self._mouseEntered()
        return super(HiddenToolButton, self).enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouseLeft()
        return super(HiddenToolButton, self).leaveEvent(event)

if __name__ == '__main__':
    from lunchinator.plugin import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : RemotePicturesGui(window, True, 0.2, 0.8))
