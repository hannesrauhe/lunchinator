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
        
    def show_options(self):        
        d = gtk.Dialog(title="Activate Plugin")
        d.add_buttons("Save & Activate",1,"Save & Deactivate",0,"Cancel",-1)
        resp = d.run()
        d.destroy()
        if resp==-1:
            return self.is_activated
        else:
            return resp
        
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