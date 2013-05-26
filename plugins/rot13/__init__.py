from yapsy.PluginManager import PluginManagerSingleton
from iface_plugins import *
from rot13 import *

class rot13(iface_gui_plugin):
    ls = None
    
    def __init__(self):
        super(rot13, self).__init__()
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
        return rot13box().create_widget()
    
    def add_menu(self,menu):
        pass