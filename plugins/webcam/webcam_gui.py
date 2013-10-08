import urllib2, sys
from lunchinator import log_exception
from PyQt4.QtGui import QImage, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import QTimer, Qt
class UpdatingImage(QLabel):
    def __init__(self,parent,fallback_pic,pic_url,timeout,no_proxy,smooth_scaling):
        super(UpdatingImage, self).__init__(parent)
        
        self.rawPixmap = None
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.timeout = int(timeout)*1000
        self.no_proxy = no_proxy
        self.smooth_scaling = smooth_scaling
        self.setAlignment(Qt.AlignCenter)
        #self.setScaledContents(True)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        try:     
            qtimage = QImage(self.fallback_pic)
            self.rawPixmap = QPixmap.fromImage(qtimage) 
            self.setScaledPixmap()
            updateImageTimer = QTimer(self)
            updateImageTimer.setInterval(self.timeout)
            updateImageTimer.timeout.connect(self.update)
            updateImageTimer.start(self.timeout)
        except:
            log_exception("Something went wrong when trying to display the fallback image",self.fallback_pis,sys.exc_info()[0])
            
    def setScaledPixmap(self):
        # set a scaled pixmap to a w x h window keeping its aspect ratio 
        if self.rawPixmap != None:
            self.setPixmap(self.rawPixmap.scaled(self.width(),self.height(),Qt.KeepAspectRatio,Qt.SmoothTransformation if self.smooth_scaling else Qt.FastTransformation))
    
    def resizeEvent(self, event):
        super(UpdatingImage, self).resizeEvent(event)
        self.setScaledPixmap()
    
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
            
            self.rawPixmap = QPixmap.fromImage(qtimage)
            self.setScaledPixmap()
            return True
        except:
            log_exception("Something went wrong when trying to display the webcam image")
            return False