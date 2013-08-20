
from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton

'''use iface_called_plugin if you want to do something when a message arrives
(see notify.py for example)'''

class example_called(iface_called_plugin):    
    def __init__(self):
        super(example_called, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        '''specify parametes and there default values here - 
        they can be changed in the settings tab of your plugin and are saved to disk'''
        self.options={"int_option":3,"stirng_option":"yes"}
        
    def activate(self):
        iface_called_plugin.activate(self)
        '''do something when the user activates the plugin'''        
        
        '''if you want to exchange information between plugins at run-time, 
        you can write it to this dictionary -
        use unique keys, collisions are not handled by the main programm, 
        in fact, the lunchinator itself ignores this dict completely'''        
        self.shared_dict={"exmaple_plugin_info":42}
        
        '''to send a message'''
        self.ls.call_all_members("this is a message sent by the example plugin")
        
        '''to send an event'''
        self.ls.call_all_members("HELO_EXAMPLE an event of typ HELO_EXAMPLE")
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        '''do something when the user deactivates the plugin'''
        del self.shared_dict["exmaple_plugin_info"]
        
    def process_message(self,msg,addr,member_info):
        '''if a text-message comes in, this method will be called'''
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        '''if a text-message that is recognized as lunch call comes in, this method will be called'''
        
        '''you can use the logger to write information to the log-files'''
        self.logger.info("my plugin processes the lunch call")
        if 0==1:
            self.logger.error("something went wrong")
            
        '''if exceptions are thrown they will be caught and logged outside'''
    
    def process_event(self,cmd,value,ip,member_info):
        '''messages that are exchanged between peers to inform 
        about preferred lunch time, avatars, etc can be processed in this method'''
        pass
    
'''this will display some GTK widget in a tab of the lunchinator
(see lunch_menu.py for example)'''
class example_gui(iface_gui_plugin):
    def create_widget(self):
        return gtk.Label("Somehting that will show up in the lunchinator")
    pass


'''if you just want something to run, while the lunchinator is running, use a general plugin
(see lunch_menu.yp for example)'''
class example_general(iface_general_plugin):
    pass