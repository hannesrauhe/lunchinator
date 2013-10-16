from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings
import urllib2,sys
    
class webcam(iface_gui_plugin):
    def __init__(self):
        super(webcam, self).__init__()
        self.options = [(("fallback_pic", "Fallback image file"), get_settings().get_lunchdir()+"/images/webcam.jpg"),
                        (("pic_url", "Image URL"),"http://lunchinator.de/files/webcam_dummy.jpg"),
                        (("timeout", "Timeout"),5),
                        (("no_proxy", "Don't use proxy server"),False),
                        (("smooth_scaling", "Smooth scaling", self.smoothScalingChanged),False)]
        self.webcam = None
        
    def smoothScalingChanged(self, _setting, newValue):
        self.webcam.smooth_scaling = newValue
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from webcam.webcam_gui import UpdatingImage
        self.webcam = UpdatingImage(parent, self.options["fallback_pic"],self.options["pic_url"],self.options["timeout"],self.options["no_proxy"],self.options["smooth_scaling"])
        return self.webcam
    
    def add_menu(self,menu):
        pass
