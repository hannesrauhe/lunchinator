from lunchinator.iface_plugins import *
from rot13 import *
from lunchinator import get_server
from PyQt4.QtGui import QImage, QPixmap, QLabel
from PyQt4.QtCore import Qt

class rot13(iface_gui_plugin):
    def __init__(self):
        super(rot13, self).__init__()
        self.w = rot13box()
        self.maxwidth=400
        self.maxheight=400
#        self.options = {"fallback_pic":sys.path[0]+"/images/webcam.jpg",
#                        "pic_url":"http://webcam.wdf.sap.corp:1080/images/canteen_bac.jpeg",
#                        "timeout":5}
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        if (len(get_server().last_messages)):
            self.w.encodeText(get_server().get_last_msgs()[0][2])
        add_widget = None
        if self.shared_dict.has_key("tdtnotify_file"):
            try:
                qtimage = QImage(self.shared_dict["tdtnotify_file"])
                
                width = self.maxwidth
                height = qtimage.height()*self.maxwidth/qtimage.width()
                if height>self.maxheight:
                    height = self.maxheight
                    width = qtimage.width()*self.maxheight/qtimage.height()
                # TODO use different scaling parameters?
                qtimage = qtimage.scaled(width, height, aspectRatioMode=Qt.IgnoreAspectRatio, transformMode=Qt.FastTransformation)
                add_widget = QLabel()
                add_widget.setPixmap(QPixmap.fromImage(qtimage))
            except:
                log_exception("Error creating image label")
        return self.w.create_widget(parent, add_widget)
            
    def add_menu(self,menu):
        pass