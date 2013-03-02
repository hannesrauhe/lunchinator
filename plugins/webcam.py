
from iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
import gtk,gobject,urllib2,sys
    
class webcam(iface_gui_plugin):
    ls = None
    
    def __init__(self):
        super(webcam, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_gui_plugin.activate(self)
        if self.hasConfigOption("fallback_pic"):
            self.setConfigOption("fallback_pic",sys.path[0]+"/images/webcam.jpg" )
        if self.hasConfigOption("pic_url"):
            self.setConfigOption("pic_url","http://webcam.wdf.sap.corp:1080/images/canteen_bac.jpeg" )
        if self.hasConfigOption("timeout"):
            self.setConfigOption("timeout","5" )
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def add_vertical(self, box):
        pass
    
    def add_horizontal(self, box):
        webcam = UpdatingImage(box,self.getConfigOption("fallback_pic"),self.getConfigOption("pic_url"),int(self.getConfigOption("timeout")))
    
    def add_menu(self,menu):
        pass
    
    

class UpdatingImage():
    pic_url = None
    timeout = 5
    fallback_pic = None
    def __init__(self,box,fallback_pic,pic_url,timeout):
        try:     
            self.gtkimage = gtk.Image() 
            self.gtkimage.set_from_file(self.fallback_pic)
            self.gtkimage.show()
            box.pack_start(self.gtkimage, True, True, 0)
            gobject.timeout_add(self.timeout, self.update)        
        except:
            print "Something went wrong when trying to display the fallback image",self.ls.show_pic_fallback
            pass      
            
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