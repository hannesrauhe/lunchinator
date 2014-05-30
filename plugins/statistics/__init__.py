from lunchinator.iface_plugins import *
from lunchinator import get_server, log_debug,\
    get_settings, get_db_connection, log_warning, \
    get_notification_center
import threading

class statistics(iface_called_plugin):
    def __init__(self):
        super(statistics, self).__init__()
        self.options = [((u"db_connection", u"DB Connection", 
                          get_settings().get_available_db_connections(),
                          self.connect_to_db),
                         get_settings().get_default_db_connection())]
        self.connectionPlugin = None
        self.connect_lock = threading.Lock()
    
    def activate(self):
        iface_called_plugin.activate(self)
        get_notification_center().connectDBSettingChanged(self.connect_to_db)
        get_notification_center().connectDBConnReady(self.connect_to_db)
        get_notification_center().connectPeerAppended(self.peer_update)
        get_notification_center().connectPeerUpdated(self.peer_update)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def connect_to_db(self, changedDBConn = None):
        with self.connect_lock:
            if self.connectionPlugin and changedDBConn and changedDBConn != self.options["db_connection"]:
                return
            dbPlugin, plugin_type = get_db_connection(self.options["db_connection"])
            
            if not dbPlugin:
                log_error("Statistics: DB  connection %s not available: Activate a DB Connection plugin and check settings"
                          %(self.options["db_connection"]))
                return False
            
            if plugin_type == "SQLite Connection":
                self.connectionPlugin = statistics_sqlite(dbPlugin)
                log_debug("Statistics: Using DB Connection ",type(plugin_type))
            else:
                self.connectionPlugin = None
                return False
                        
            return True
        
    def is_db_ready(self):
        return self.connectionPlugin and self.connectionPlugin.isOpen()
    
    def process_message(self,msg,addr,member_info):
        if self.is_db_ready():
            self.connectionPlugin.insert_call("msg", msg, addr)
        else:
            log_warning("Statistics: DB not ready -- cannot process message")
            
    def process_lunch_call(self,msg,ip,member_info):
        if self.is_db_ready():
            self.connectionPlugin.insert_call("lunch", msg, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process lunch_call")
    
    def process_event(self,cmd,value,ip,member_info):
        if self.is_db_ready():
            self.connectionPlugin.insert_call(cmd, value, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process event")
            
    def peer_update(self, peerID, peerInfo):        
        if self.is_db_ready():
            self.connectionPlugin.insert_members("ip", peerInfo["name"], \
                                 peerInfo["avatar"], peerInfo["next_lunch_begin"], peerInfo["next_lunch_end"])
        else:
            log_warning("Statistics: DB not ready -- cannot store member data")
            
class statistics_dbase(object):
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
    
    def isOpen(self):
        if self.dbConn:
            return self.dbConn.isOpen()
        return False

class statistics_sqlite(statistics_dbase):
    messages_schema = "CREATE TABLE messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, rtime INTEGER)"
    members_schema = "CREATE TABLE members (IP TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    
        
    def insert_call(self,mtype,msg,sender):
        self.dbConn.execute("INSERT INTO messages(mtype,message,sender,rtime) VALUES (?,?,?,strftime('%s', 'now'))",mtype,msg,sender)
    
    def insert_members(self,ip,name,avatar,lunch_begin,lunch_end):
        self.dbConn.execute("INSERT INTO members(IP, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,strftime('%s', 'now'))",ip,name,avatar,lunch_begin,lunch_end)
        
    def get_newest_members_data(self):    
        return self.dbConn.query("SELECT IP,name,avatar,lunch_begin,lunch_end,MAX(rtime) FROM members GROUP BY IP")
