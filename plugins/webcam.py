from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception
import urllib2,sys
from PyQt4.QtGui import QImage, QPixmap, QLabel
from PyQt4.QtCore import QTimer
    
class webcam(iface_gui_plugin):
    def __init__(self):
        super(webcam, self).__init__()
        self.options = {"fallback_pic":sys.path[0]+"/images/webcam.jpg",
                        "pic_url":"http://lunchinator.de/files/webcam_dummy.jpg",
                        "timeout":5,
                        "no_proxy":False}
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        webcam = UpdatingImage(parent, self.options["fallback_pic"],self.options["pic_url"],self.options["timeout"],self.options["no_proxy"])
        return webcam
    
    def add_menu(self,menu):
        pass
    
class UpdatingImage(QLabel):
    def __init__(self,parent,fallback_pic,pic_url,timeout,no_proxy):
        super(UpdatingImage, self).__init__(parent)
        
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.timeout = int(timeout)*1000
        self.no_proxy = no_proxy
        try:     
            qtimage = QImage(self.fallback_pic) 
            self.setPixmap(QPixmap.fromImage(qtimage))
            updateImageTimer = QTimer(self)
            updateImageTimer.setInterval(self.timeout)
            updateImageTimer.timeout.connect(self.update)
            updateImageTimer.start(self.timeout)
        except:
            log_exception("Something went wrong when trying to display the fallback image",self.fallback_pis,sys.exc_info()[0])
            
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
            
            self.setPixmap(QPixmap.fromImage(qtimage))
            return True
        except:
            log_exception("Something went wrong when trying to display the webcam image")
            return False