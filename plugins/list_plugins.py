from lunchinator.iface_plugins import *
import gtk,gobject,urllib2,sys
    
class list_plugins(iface_gui_plugin):
    def __init__(self):
        super(list_plugins, self).__init__()
        #self.options = {"url":"http://155.56.69.85:1081/lunch_de.txt" }
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        textview = gtk.TextView()
        textview.set_size_request(400,200)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        textbuffer = textview.get_buffer()
        sw.add(textview)
        sw.show()
        textview.show()
        txt = ""
        manager = PluginManagerSingleton.get()
        for pluginInfo in manager.getAllPlugins():    
            txt+=pluginInfo.name + " - "
#            txt+=pluginInfo.path +" "
#            txt+=pluginInfo.version +" "
#            txt+=str(pluginInfo.author) +", "
#            txt+=pluginInfo.copyright +" "
#            txt+=pluginInfo.website +" "
            txt+=pluginInfo.description +" "
#            txt+=pluginInfo.details + " "
            txt+="\n\n"
        textbuffer.set_text(txt)
        return sw
    
    def add_menu(self,menu):
        pass
