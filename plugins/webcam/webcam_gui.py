import sys
from lunchinator import log_exception, log_error
from PyQt4.QtGui import QImage, QPixmap
from PyQt4.QtCore import QTimer, QSize, QThread, pyqtSlot
from lunchinator.resizing_image_label import ResizingImageLabel
from lunchinator.download_thread import DownloadThread

class UpdatingImage(ResizingImageLabel):
    def __init__(self,parent,fallback_pic,pic_url,timeout,no_proxy,smooth_scaling):
        super(UpdatingImage, self).__init__(parent, smooth_scaling, QSize(640, 480))
        
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.timeout = int(timeout)*1000
        self.no_proxy = no_proxy
        try:     
            self.setImage(self.fallback_pic)
            updateImageTimer = QTimer(self)
            updateImageTimer.setInterval(self.timeout)
            updateImageTimer.timeout.connect(self.update)
            updateImageTimer.start(self.timeout)
        except:
            log_exception("Something went wrong when trying to display the fallback image",self.fallback_pic,sys.exc_info()[0])
            
    @pyqtSlot(QThread, unicode)
    def downloadFinished(self, thread, _url):
        qtimage = QImage()
        qtimage.loadFromData(thread.getResult())
        self.setRawPixmap(QPixmap.fromImage(qtimage))
            
    @pyqtSlot(QThread, unicode)
    def errorDownloading(self, _thread, url):
        log_error("Error downloading webcam image from %s" % url)
            
    def update(self): 
        thread = DownloadThread(self, self.pic_url)
        thread.finished.connect(thread.deleteLater)
        thread.error.connect(self.errorDownloading)
        thread.success.connect(self.downloadFinished)
        thread.start()
        return True
