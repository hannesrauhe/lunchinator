from lunchinator.iface_plugins import *
from lunchinator import get_server, log_debug,\
    get_settings, get_db_connection, log_warning, \
    get_notification_center
import threading

class statistics(iface_called_plugin):
    def __init__(self):
        super(statistics, self).__init__()
        self.options = [((u"db_connection", u"DB Connection", 
                          get_settings().get_available_db_connections()),
                         get_settings().get_default_db_connection())]
        self.connectionPlugin = None
        self.connect_lock = threading.Lock()
    
    def activate(self):
        iface_called_plugin.activate(self)
        get_notification_center().connectDBSettingChanged(self.connect_to_db)
        get_notification_center().connectDBConnReady(self.connect_to_db)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def connect_to_db(self, changedDBConn = None):
        with self.connect_lock:
            if self.connectionPlugin and changedDBConn and changedDBConn != self.options["db_connection"]:
                return
            self.connectionPlugin, plugin_type = get_db_connection(self.options["db_connection"])
                
            if None==self.connectionPlugin:
                log_error("Statistics: DB  connection %s not available - will deactivate statistics now"
                          %(self.options["db_connection"]))
                log_error("Statistics: Activate a DB Connection plugin and check settings")
                return False
            
            log_debug("Statistics: Using DB Connection ",type(self.connectionPlugin))
            return True
            
    def process_message(self,msg,addr,member_info):
        if self.connectionPlugin.db_ready and self.connectionPlugin.isOpen():
            self.connectionPlugin.insert_call("msg", msg, addr)
        else:
            log_warning("Statistics: DB not ready -- cannot process message")
            
    def process_lunch_call(self,msg,ip,member_info):
        if self.connectionPlugin.db_ready and self.connectionPlugin.isOpen():
            self.connectionPlugin.insert_call("lunch", msg, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process message")
    
    def process_event(self,cmd,value,ip,member_info):
        if self.connectionPlugin and self.connectionPlugin.isOpen():
            self.connectionPlugin.insert_call(cmd, value, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process message")

class statistics_sqlite(object):
    messages_schema = "CREATE TABLE messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, rtime INTEGER)"
    members_schema = "CREATE TABLE members (IP TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    
    def __init__(self, newconn):
        self.dbConn = newconn
        
        try:            
            if not newconn.existsTable("members"):
                newconn.execute(self.members_schema)
            if not newconn.existsTable("messages"):
                newconn.execute(self.messages_schema)
        except:
            log_exception("Problem while initializing database in SQLite")  
            raise 
        
        
    def insert_call(self,mtype,msg,sender):
        self.dbConn.execute("INSERT INTO messages(mtype,message,sender,rtime) VALUES (?,?,?,strftime('%s', 'now'))",mtype,msg,sender)
    
    def insert_members(self,ip,name,avatar,lunch_begin,lunch_end):
        self.dbConn.execute("INSERT INTO members(IP, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,strftime('%s', 'now'))",ip,name,avatar,lunch_begin,lunch_end)
        
    def get_newest_members_data(self):    
        return self.dbConn.query("SELECT IP,name,avatar,lunch_begin,lunch_end,MAX(rtime) FROM members GROUP BY IP")
