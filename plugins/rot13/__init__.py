from yapsy.PluginManager import PluginManagerSingleton
from lunchinator.iface_plugins import *
from rot13 import *

class rot13(iface_gui_plugin):
    ls = None
    
    def __init__(self):
        super(rot13, self).__init__()
        self.w = rot13box()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
#        self.options = {"fallback_pic":sys.path[0]+"/images/webcam.jpg",
#                        "pic_url":"http://webcam.wdf.sap.corp:1080/images/canteen_bac.jpeg",
#                        "timeout":5}
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        if (len(self.ls.last_messages)):
            self.w.encodeText(self.ls.get_last_msgs()[0][2])
        return self.w.create_widget()
    
    def add_menu(self,menu):
        pass