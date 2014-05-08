from PyQt4.QtGui import QImage, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import Qt, QSize, QThread, pyqtSlot, QTimer
import sys
from lunchinator import log_exception, log_error
from lunchinator.download_thread import DownloadThread

class ResizingImageLabel(QLabel):
    def __init__(self,parent,smooth_scaling,sizeHint = None):
        super(ResizingImageLabel, self).__init__(parent)
        
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

class ResizingWebImageLabel(ResizingImageLabel):
    """Constructor
    
    parent -- parent QObject
    pic_url -- URL to download and display
    fallback_pic -- Picture to display if pic_url is not yet downloaded or is not available
    smooth_scaling -- Use a smooth image resizing algorithm (slower)
    update -- automatically update periodically
    timeout -- number of seconds between updates
    no_proxy -- True to disable proxy for pic_url
    """
    def __init__(self, parent, pic_url = None, fallback_pic = None, smooth_scaling = False, update = False, timeout = 0, no_proxy = False):
        super(ResizingWebImageLabel, self).__init__(parent, smooth_scaling, QSize(640, 480))
        
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.no_proxy = no_proxy
        
        self._displayFallbackPic()
                
        self.timeout = int(timeout)*1000
        if update:
            updateImageTimer = QTimer(self)
            updateImageTimer.setInterval(self.timeout)
            updateImageTimer.timeout.connect(self.update)
            updateImageTimer.start(self.timeout)
            
    def _displayFallbackPic(self):
        if self.fallback_pic != None:
            try:
                self.setImage(self.fallback_pic)
            except:
                log_exception("Something went wrong when trying to display the fallback image",self.fallback_pic)
        else:
            self.setPixmap(QPixmap())
            
    def setURL(self, newURL):
        self._displayFallbackPic()
        self.pic_url = newURL
        self.update()
            
    @pyqtSlot(QThread, unicode)
    def downloadFinished(self, thread, _url):
        qtimage = QImage()
        qtimage.loadFromData(thread.getResult())
        self.setRawPixmap(QPixmap.fromImage(qtimage))
            
    @pyqtSlot(QThread, unicode)
    def errorDownloading(self, _thread, url):
        log_error("Error downloading webcam image from %s" % url)
        
    def showEvent(self, event):
        self.update()
        return super(ResizingWebImageLabel, self).showEvent(event)
            
    def update(self):
        if not self.isVisible():
            return
         
        if self.pic_url != None:
            thread = DownloadThread(self, self.pic_url, no_proxy = self.no_proxy)
            thread.finished.connect(thread.deleteLater)
            thread.error.connect(self.errorDownloading)
            thread.success.connect(self.downloadFinished)
            thread.start()
        else:
            self._displayFallbackPic()
        return True
