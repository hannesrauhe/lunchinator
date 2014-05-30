from lunchinator.iface_plugins import *
from lunchinator import get_server, log_debug,\
    get_settings, get_db_connection, log_warning, \
    get_notification_center, get_peers
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
                log_debug("Statistics: Using DB Connection ",plugin_type)
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
            self.migrate()
        except:
            log_exception("Problem while migrating dataset to new version")
    
    def isOpen(self):
        if self.dbConn:
            return self.dbConn.isOpen()
        return False
    
    def migrate(self):
        raise NotImplementedError("Migration not implmented")

class statistics_sqlite(statistics_dbase):
    version_schema = "CREATE TABLE statistics_version (commit_count INTEGER, migrate_time INTEGER)"
    messages_schema = "CREATE TABLE statistics_messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, senderIP TEXT, rtime INTEGER)"
    members_schema = "CREATE TABLE statistics_members (peerID TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    
    def migrate(self):                   
        if not self.dbConn.existsTable("statistics_version"):
            self.dbConn.execute(self.version_schema)
            if self.dbConn.existsTable("messages"):
                #migrate from first version
                #create tables with statistics_prefix
                self.dbConn.execute("ALTER TABLE messages RENAME TO statistics_messages")
                self.dbConn.execute("ALTER TABLE statistics_messages ADD COLUMN senderIP TEXT DEFAULT \"\" ") 
                self.dbConn.execute("UPDATE statistics_messages SET senderIP=sender WHERE senderIP=\"\"")
                self.dbConn.execute("CREATE TABLE statistics_members (peerID TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)")
                self.dbConn.execute("INSERT INTO statistics_members SELECT * FROM members") 
                self.dbConn.execute("INSERT INTO statistics_version VALUES (1300, strftime('%s', 'now'))")
        
        #in case no migration has happened create empty tables
        if not self.dbConn.existsTable("statistics_members"):
            self.dbConn.execute(self.members_schema)
        if not self.dbConn.existsTable("statistics_messages"):
            self.dbConn.execute(self.messages_schema)
            
    def insert_call(self,mtype,msg,senderIP):
        senderID = get_peers().getPeerID(pIP=senderIP)
        self.dbConn.execute("INSERT INTO statistics_messages(mtype,message,sender,senderIP,rtime) VALUES (?,?,?,?,strftime('%s', 'now'))",mtype,msg,senderID,senderIP)
    
    def insert_members(self,peer_id,name,avatar,lunch_begin,lunch_end):
        self.dbConn.execute("INSERT INTO statistics_members(peerID, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,strftime('%s', 'now'))",peer_id,name,avatar,lunch_begin,lunch_end)
        
    def get_newest_members_data(self):    
        return self.dbConn.query("SELECT peerID,name,avatar,lunch_begin,lunch_end,MAX(rtime) FROM statistics_members GROUP BY peerID")
    
#class statistics_hana(statistics_dbase):
