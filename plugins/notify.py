from iface_called_plugin import *

class Notify(iface_called_plugin):
    def process_message(self,msg,ip,member_info):
        print msg
        
    def process_event(self,msg,ip,member_info):
        print msg