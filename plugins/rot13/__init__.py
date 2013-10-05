from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, log_exception

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
        from PyQt4.QtGui import QImage, QPixmap, QLabel
        from PyQt4.QtCore import Qt
        from rot13 import rot13box
        
        w = rot13box(parent)
        if get_server().messagesCount() > 0:
            w.encodeText(get_server().getMessage(0)[2])
        add_widget = None
        if self.shared_dict.has_key("tdtnotify_file"):
            try:
                qtimage = QImage(self.shared_dict["tdtnotify_file"])
                if qtimage.width() > 0 and qtimage.height() > 0:
                    width = self.maxwidth
                    height = qtimage.height()*self.maxwidth/qtimage.width()
                    if height>self.maxheight:
                        height = self.maxheight
                        width = qtimage.width()*self.maxheight/qtimage.height()
                    qtimage = qtimage.scaled(width, height, aspectRatioMode=Qt.IgnoreAspectRatio, transformMode=Qt.SmoothTransformation)
                    add_widget = QLabel()
                    add_widget.setPixmap(QPixmap.fromImage(qtimage))
            except:
                log_exception("Error creating image label")
        return w.create_widget(parent, add_widget)
            
    def add_menu(self,menu):
        pass