from yapsy.IPlugin import IPlugin
import gtk

class iface_plugin(IPlugin):
    def activate(self):
        """
        Call the parent class's acivation method
        """
        IPlugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        IPlugin.deactivate(self)
        
    def create_options_widget(self):
        w = gtk.VBox()
        w.pack_start(gtk.Label("Options will go here - change $HOME/.lunchinator/settings.cfg manually for now"))
        return w
        
class iface_gui_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's acivation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
    def create_widget(self):
        return gtk.Label("The plugin should show its content here")
    
    def add_menu(self,menu):
        pass

class iface_called_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's acivation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass