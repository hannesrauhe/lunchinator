from lunchinator.iface_plugins import iface_general_plugin
import gtk
from l_avatar import l_avatar
from lunchinator import get_server, get_settings

class avatar(iface_general_plugin):
    def __init__(self):
        super(avatar, self).__init__()
        
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
    
    def add_menu(self,menu):
        pass    
    
    def _chooseFile(self,gtkimg):        
        dialog = gtk.FileChooserDialog(title="Choose Avatar Picture",action=gtk.FILE_CHOOSER_ACTION_OPEN,
                            buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        
        fi = gtk.FileFilter()
        fi.set_name("Images")
        fi.add_mime_type("image/png")
        fi.add_mime_type("image/jpeg")
        fi.add_mime_type("image/gif")
        fi.add_pattern("*.png")
        fi.add_pattern("*.jpg")
        fi.add_pattern("*.gif")
        fi.add_pattern("*.tif")
        fi.add_pattern("*.xpm")
        dialog.add_filter(fi)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            l = l_avatar()
            gtkimg.set_from_file( l.use_as_avatar( get_server(), dialog.get_filename() ) )
        dialog.destroy()
    
    def create_options_widget(self):
        import gtk
        
        img_path = get_settings().get_avatar_dir()+get_settings().get_avatar_file()
        
        t = gtk.VBox()
        gtkimage = gtk.Image() 
        gtkimage.set_from_file(img_path)
        gtkimage.set_tooltip_text(img_path)
                
        b = gtk.Button("Choose Picture")
        b.connect_object("clicked", self._chooseFile, gtkimage)
        
        t.pack_start(b,False,False,10)
        t.pack_start(gtkimage,True,True,10)
        t.show_all()
        return t
