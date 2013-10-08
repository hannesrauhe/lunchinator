from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, log_exception

class rot13(iface_gui_plugin):
    def __init__(self):
        super(rot13, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QImage, QPixmap, QLabel
        from PyQt4.QtCore import Qt
        from rot13 import rot13box
        
        if self.shared_dict.has_key("tdtnotify_file"):
            w = rot13box(parent, self.shared_dict["tdtnotify_file"])
        else:
            w = rot13box(parent)
        if get_server().messagesCount() > 0:
            w.encodeText(get_server().getMessage(0)[2])
            
        return w
        
    def add_menu(self,menu):
        pass