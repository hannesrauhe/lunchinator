from lunchinator.plugin import *
from lunchinator import get_server

'''use iface_called_plugin if you want to do something when a message arrives
(see notify.py for example)'''

class example_called(iface_called_plugin):    
    def __init__(self):
        super(example_called, self).__init__()
        '''specify parametes and there default values here - 
        they can be changed in the settings tab of your plugin and are saved to disk'''
        self.options={"int_option":3,"stirng_option":"yes"}
        
    def activate(self):
        iface_called_plugin.activate(self)
        '''do something when the user activates the plugin'''     
        
        '''to send a message'''
        get_server().call_all_members("this is a message sent by the example plugin")
        
        '''to send an event'''
        get_server().call_all_members("HELO_EXAMPLE an event of typ HELO_EXAMPLE")
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        '''do something when the user deactivates the plugin'''
        
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
    
    def process_event(self,cmd,value,ip,member_info,prep):
        '''messages that are exchanged between peers to inform 
        about preferred lunch time, avatars, etc can be processed in this method'''
        pass
    
'''this will display some GTK widget in a tab of the lunchinator
(see lunch_menu.py for example)'''
class example_gui(iface_gui_plugin):
    def create_widget(self, parent):
        import PyQt4
        return PyQt4.QtGui.QLabel("Somehting that will show up in the lunchinator", parent)
    pass


'''if you just want something to run, while the lunchinator is running, use a general plugin
(see lunch_menu.yp for example)'''
class example_general(iface_general_plugin):
    pass