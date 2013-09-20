from lunchinator.iface_plugins import *
from rot13 import *
from lunchinator import get_server

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
    
    def create_widget(self):
        if (len(get_server().last_messages)):
            self.w.encodeText(get_server().get_last_msgs()[0][2])
        gtkimage = None
        if self.shared_dict.has_key("tdtnotify_file"):
            try:
                gtkimage = gtk.Image() 
                pixbuf = gtk.gdk.pixbuf_new_from_file(self.shared_dict["tdtnotify_file"])
                width = self.maxwidth
                height = pixbuf.get_height()*self.maxwidth/pixbuf.get_width()
                if height>self.maxheight:
                    height = self.maxheight
                    width = pixbuf.get_width()*self.maxheight/pixbuf.get_height()
                pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
                gtkimage.set_from_pixbuf(pixbuf)
            except:
                gtkimage=None
        return self.w.create_widget(gtkimage)
            
    def add_menu(self,menu):
        pass