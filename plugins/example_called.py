
from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton

class twitter_status(iface_called_plugin):
    s_thread = None
    ls = None
    
    def __init__(self):
        super(twitter_status, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_called_plugin.activate(self)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        pass