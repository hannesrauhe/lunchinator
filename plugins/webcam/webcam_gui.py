import urllib2, sys
from lunchinator import log_exception
from PyQt4.QtGui import QImage, QPixmap
from PyQt4.QtCore import QTimer, QSize
from lunchinator.resizing_image_label import ResizingImageLabel

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
            
    def update(self): 
        try:
            response = None
            if self.no_proxy:
                proxy_handler = urllib2.ProxyHandler({})
                opener = urllib2.build_opener(proxy_handler)
                response=opener.open(self.pic_url)
            else:
                response = urllib2.urlopen(self.pic_url)
            
            qtimage = QImage()
            qtimage.loadFromData(response.read())
            
            self.setRawPixmap(QPixmap.fromImage(qtimage))
            return True
        except:
            log_exception("Something went wrong when trying to display the webcam image")
            return False