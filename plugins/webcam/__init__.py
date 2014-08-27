from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_settings
import sys
    
class webcam(iface_gui_plugin):
    def __init__(self):
        super(webcam, self).__init__()
        self.options = [(("fallback_pic", "Fallback image file"), get_settings().get_resource("images", "webcam.jpg")),
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
        from lunchinator.gui_elements import ResizingWebImageLabel
        self.webcam = ResizingWebImageLabel(parent=parent,
                                            logger=self.logger,
                                            fallback_pic=self.options["fallback_pic"],
                                            pic_url=self.options["pic_url"],
                                            timeout=self.options["timeout"],
                                            no_proxy=self.options["no_proxy"],
                                            smooth_scaling=self.options["smooth_scaling"],
                                            update=True)
        return self.webcam
    
    def add_menu(self,menu):
        pass
