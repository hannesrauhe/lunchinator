from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings
import urllib2,sys
    
class webcam(iface_gui_plugin):
    def __init__(self):
        super(webcam, self).__init__()
        self.options = {"fallback_pic":get_settings().get_lunchdir()+"/images/webcam.jpg",
                        "pic_url":"http://lunchinator.de/files/webcam_dummy.jpg",
                        "timeout":5,
                        "no_proxy":False}
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from webcam.webcam_gui import UpdatingImage
        webcam = UpdatingImage(parent, self.options["fallback_pic"],self.options["pic_url"],self.options["timeout"],self.options["no_proxy"])
        return webcam
    
    def add_menu(self,menu):
        pass
