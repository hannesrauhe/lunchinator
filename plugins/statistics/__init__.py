from lunchinator.iface_plugins import *
import sys
from lunchinator import get_server, log_exception, log_error, log_debug

class statistics(iface_called_plugin):
    def __init__(self):
        super(statistics, self).__init__()
        self.options = [(("db_connect", "Which db connection to use (leave empty for default)",self.connect_to_db),"")]
        self.connectionPlugin = None
    
    def activate(self):
        iface_called_plugin.activate(self)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def connect_to_db(self,_=None,__=None):
        self.connectionPlugin = get_server().getDBConnection(self.options["db_connect"])
            
        log_debug("Statistics: Using DB Connection ",type(self.connectionPlugin))
            
        if None==self.connectionPlugin:
            log_error("Statistics: DB %s connection not available - will deactivate statistics now"%self.options["db_connect"])
            log_error("Statistics: Activate a DB Connection plugin and check settings")
            return False
        return True
            
    def process_message(self,msg,addr,member_info):
        if self.connectionPlugin or self.connect_to_db():
            self.connectionPlugin.insert_call("msg", msg, addr)
            
    def process_lunch_call(self,msg,ip,member_info):
        if self.connectionPlugin or self.connect_to_db():
            self.connectionPlugin.insert_call("lunch", msg, ip)
    
    def process_event(self,cmd,value,ip,member_info):
        if self.connectionPlugin or self.connect_to_db():
            self.connectionPlugin.insert_call(cmd, value, ip)
        
        #ignore member stuff for now
#        if ip not in self.members():
#            name = member_info['name'] if "name" in member_info else ""
#            avatar = member_info['avatar'] if "avatar" in member_info else ""
#            lunch_begin = member_info['next_lunch_begin'] if "next_lunch_begin" in member_info else ""
#            lunch_end = member_info['next_lunch_end'] if "next_lunch_end" in member_info else ""
#            self.members()[ip]=(ip, name, avatar, lunch_begin, lunch_end)
#            stats.insert_members(ip, name, avatar, lunch_begin, lunch_end)
#        else:
#            if cmd=="HELO": 
#                if self.members()[ip][1]!=value:
#                    stats.insert_members(ip, value, self.members()[ip][2], self.members()[ip][3], self.members()[ip][4])
#                    self.members()[ip]=(ip, value, self.members()[ip][2], self.members()[ip][3], self.members()[ip][4])
#            elif cmd in ["HELO_INFO","HELO_REQUEST_DICT"]:
#                if (self.members()[ip][1]!=member_info['name'] or
#                        self.members()[ip][2]!=member_info['avatar'] or 
#                        self.members()[ip][3]!=member_info['next_lunch_begin'] or 
#                        self.members()[ip][4]!=member_info['next_lunch_end']):
#                    stats.insert_members(ip, member_info['name'], member_info['avatar'], member_info['next_lunch_begin'], member_info['next_lunch_end'])
#                    self.members()[ip]=(ip, member_info['name'], member_info['avatar'], member_info['next_lunch_begin'], member_info['next_lunch_end'])
                   
