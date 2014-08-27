from PyQt4.QtGui import QImage, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import Qt, QSize, QThread, QTimer, pyqtSignal
from lunchinator.download_thread import DownloadThread
from lunchinator.log.logging_slot import loggingSlot

class ResizingImageLabel(QLabel):
    def __init__(self, parent, logger, smooth_scaling, sizeHint=None):
        super(ResizingImageLabel, self).__init__(parent)
        
        self.logger = logger
        self._sizeHint = sizeHint
        self.rawPixmap = None
        self.smooth_scaling = smooth_scaling
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setMinimumSize(50, 50)
            
    def sizeHint(self):
        if self._sizeHint == None:
            return QLabel.sizeHint(self)
        return self._sizeHint
            
    def setScaledPixmap(self):
        # set a scaled pixmap to a w x h window keeping its aspect ratio 
        if self.rawPixmap != None:
            self.setPixmap(self.rawPixmap.scaled(self.width(),self.height(),Qt.KeepAspectRatio,Qt.SmoothTransformation if self.smooth_scaling else Qt.FastTransformation))
    
    def resizeEvent(self, event):
        self.setScaledPixmap()
        super(ResizingImageLabel, self).resizeEvent(event)
    
    def setRawPixmap(self, pixmap):
        self.rawPixmap = pixmap
        self.setScaledPixmap()
    
    def setImage(self, path):
        self.setRawPixmap(QPixmap.fromImage(QImage(path)))
        
    def setSmoothScaling(self, newValue):
        if self.smooth_scaling != newValue:
            self.smooth_scaling = newValue
            self.setScaledPixmap()

class ResizingWebImageLabel(ResizingImageLabel):
    imageDownloaded = pyqtSignal(object, object) # url, image data as str
    
    def __init__(self, parent, logger, pic_url=None, fallback_pic=None, smooth_scaling=False, update=False, timeout=0, no_proxy=False):
        """Constructor
        
        @param parent: parent QObject
        @param pic_url -- URL to download and display
        @param fallback_pic -- Picture to display if pic_url is not yet downloaded or is not available
        @param smooth_scaling -- Use a smooth image resizing algorithm (slower)
        @param update -- automatically update periodically
        @param timeout -- number of seconds between updates
        @param no_proxy -- True to disable proxy for pic_url
        """
        super(ResizingWebImageLabel, self).__init__(parent, logger, smooth_scaling, QSize(640, 480))
        
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.pic_path = None
        self.no_proxy = no_proxy
        
        self.displayFallbackPic()
                
        self.timeout = int(timeout)*1000
        if update:
            updateImageTimer = QTimer(self)
            updateImageTimer.setInterval(self.timeout)
            updateImageTimer.timeout.connect(self.update)
            updateImageTimer.start(self.timeout)
            
    def displayFallbackPic(self):
        if self.fallback_pic != None:
            try:
                self.setImage(self.fallback_pic)
            except:
                self.logger.exception("Something went wrong when trying to display the fallback image %s", self.fallback_pic)
        else:
            self.setPixmap(QPixmap())
            
    def setURL(self, newURL):
        self.displayFallbackPic()
        self.pic_url = newURL
        self.update()
        
    def setImage(self, path):
        self.pic_path = path
        self.pic_url = None
        self.update()
            
    @loggingSlot(QThread, object)
    def downloadFinished(self, thread, url):
        self.imageDownloaded.emit(url, thread.getResult())
        qtimage = QImage()
        qtimage.loadFromData(thread.getResult())
        self.setRawPixmap(QPixmap.fromImage(qtimage))
        thread.close()
            
    @loggingSlot(QThread, object)
    def errorDownloading(self, _thread, url):
        self.logger.error("Error downloading webcam image from %s", url)
        
    def showEvent(self, event):
        self.update()
        return super(ResizingWebImageLabel, self).showEvent(event)
            
    @loggingSlot()
    def update(self):
        if not self.isVisible():
            return
         
        if self.pic_url is not None:
            thread = DownloadThread(self, self.logger, self.pic_url, no_proxy = self.no_proxy)
            thread.finished.connect(thread.deleteLater)
            thread.error.connect(self.errorDownloading)
            thread.success.connect(self.downloadFinished)
            thread.start()
        elif self.pic_path is not None:
            super(ResizingWebImageLabel, self).setImage(self.pic_path)
        else:
            self.displayFallbackPic()
        return True
