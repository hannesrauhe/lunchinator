from iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
import gtk
from lunch_avatar import lunch_avatar

class avatar(iface_general_plugin):
    ls = None
    
    def __init__(self):
        super(avatar, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
    
    def add_menu(self,menu):
        pass    
    
    def _chooseFile(self,gtkimg):
        dialog = gtk.FileChooserDialog(title="Choose Avatar Picture",action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        
        filter = gtk.FileFilter()
        filter.set_name("Pictures")
        filter.add_pattern("*")
        dialog.add_filter(filter)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            gtkimg.set_from_file( lunch_avatar().use_as_avatar( self.ls, dialog.get_filename() ) )
        elif response == gtk.RESPONSE_CANCEL:
            print 'Closed, no files selected'
        dialog.destroy()
    
    def create_options_widget(self):
        import gtk
        
        t = gtk.VBox()
        gtkimage = gtk.Image() 
        gtkimage.set_from_file(self.ls.get_avatar_dir()+self.ls.get_avatar_file())
                
        b = gtk.Button("Choose Picture")
        b.connect_object("clicked", self._chooseFile, gtkimage)
        
        
        t.pack_start(b,True,True,10)
        t.pack_start(gtkimage,True,True,10)
        t.show_all()
        return t