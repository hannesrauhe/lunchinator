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
        options = self.getConfigOptionsList(True)
        t = gtk.Table(len(options),2,True)
        i=0
        for o in options:
            v = self.getConfigOption(o)
            e = gtk.Entry()
            e.set_text(v)
            t.attach(gtk.Label(o),0,1,i,i+1)
            t.attach(e,1,2,i,i+1)
            i+=1
        return t
        
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