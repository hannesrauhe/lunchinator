from lunchinator.iface_plugins import *
import gtk,gobject,urllib2,sys
    
class lunch_menu(iface_gui_plugin):
    def __init__(self):
        super(lunch_menu, self).__init__()
        self.options = {"url":"http://lunchinator.de/files/menu_dummy.txt" }
        
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
        resp = urllib2.urlopen(self.options["url"])
        txt = resp.read()
        textbuffer.set_text(txt.decode('cp1252'))
        return sw
    
    def add_menu(self,menu):
        pass
