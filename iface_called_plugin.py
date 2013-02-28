from yapsy import IPlugin

class iface_called_plugin(IPlugin):
    def process_message(self,msg,ip,member_info):
        print msg
        
    def process_event(self,msg,ip,member_info):
        print msg