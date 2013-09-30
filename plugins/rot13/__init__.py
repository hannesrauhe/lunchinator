from lunchinator.iface_plugins import *
from rot13 import *
from lunchinator import get_server, log_exception
from PyQt4.QtGui import QImage, QPixmap

class rot13(iface_gui_plugin):
    def __init__(self):
        super(rot13, self).__init__()
        self.maxwidth=400
        self.maxheight=400
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        w = rot13box(parent)
        if (len(get_server().last_messages)):
            w.encodeText(get_server().get_last_msgs()[0][2])
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
        return w.create_widget(parent, add_widget)
            
    def add_menu(self,menu):
        pass