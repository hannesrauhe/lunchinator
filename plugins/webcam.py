from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
import gtk,gobject,urllib2,sys
    
class webcam(iface_gui_plugin):
    ls = None
    
    def __init__(self):
        super(webcam, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        self.options = {"fallback_pic":sys.path[0]+"/images/webcam.jpg",
#                        "pic_url":"http://lunchinator.de/files/webcam_dummy.jpg",
                        "timeout":5}
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        webcam = UpdatingImage(self.options["fallback_pic"],self.options["pic_url"],self.options["timeout"])
        return webcam.gtkimage
    
    def add_menu(self,menu):
        pass
    
    

class UpdatingImage():
    pic_url = None
    timeout = 5000
    fallback_pic = None
    def __init__(self,fallback_pic,pic_url,timeout):
        self.fallback_pic = fallback_pic
        self.pic_url = pic_url
        self.timeout = int(timeout)*1000
        try:     
            self.gtkimage = gtk.Image() 
            self.gtkimage.set_from_file(self.fallback_pic)
            self.gtkimage.show()
            gobject.timeout_add(self.timeout, self.update)        
        except:
            print "Something went wrong when trying to display the fallback image",self.fallback_pis,sys.exc_info()[0]
            
    def update(self): 
        try:
            #todo disable proxy for now
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            response=opener.open(self.pic_url)
            loader=gtk.gdk.PixbufLoader()
            loader.write(response.read())
            loader.close()   
            self.gtkimage.set_from_pixbuf(loader.get_pixbuf())  
            return True             
        except:
            print "Something went wrong when trying to display the webcam image"
            return False