from PyQt4.QtGui import QImage, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import Qt

class ResizingImageLabel(QLabel):
    def __init__(self,parent,smooth_scaling,sizeHint = None):
        super(ResizingImageLabel, self).__init__(parent)
        
        self._sizeHint = sizeHint
        self.rawPixmap = None
        self.smooth_scaling = smooth_scaling
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            
    def sizeHint(self):
        if self._sizeHint == None:
            return QLabel.sizeHint(self)
        return self._sizeHint
            
    def setScaledPixmap(self):
        # set a scaled pixmap to a w x h window keeping its aspect ratio 
        if self.rawPixmap != None:
            self.setPixmap(self.rawPixmap.scaled(self.width(),self.height(),Qt.KeepAspectRatio,Qt.SmoothTransformation if self.smooth_scaling else Qt.FastTransformation))
    
    def resizeEvent(self, event):
        super(ResizingImageLabel, self).resizeEvent(event)
        self.setScaledPixmap()
    
    def setRawPixmap(self, pixmap):
        self.rawPixmap = pixmap
        self.setScaledPixmap()
    
    def setImage(self, path):
        self.setRawPixmap(QPixmap.fromImage(QImage(path)))
