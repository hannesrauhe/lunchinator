from lunchinator.plugin import iface_called_plugin, db_for_plugin_iface
from lunchinator import get_server, log_debug,\
    get_settings, get_db_connection, log_warning, \
    get_notification_center, get_peers

class statistics(iface_called_plugin):
    def __init__(self):
        super(statistics, self).__init__()
        self.options = [((u"db_connection", u"DB Connection", 
                          get_settings().get_available_db_connections(),
                          self.reconnect_db),
                         get_settings().get_default_db_connection())]
        self.add_supported_dbms("SQLite Connection", statistics_sqlite)
        self.add_supported_dbms("SAP HANA Connection", statistics_hana)
    
    def activate(self):
        iface_called_plugin.activate(self)
        get_notification_center().connectPeerAppended(self.peer_update)
        get_notification_center().connectPeerUpdated(self.peer_update)
        
    def deactivate(self):
        get_notification_center().disconnectPeerAppended(self.peer_update)
        get_notification_center().disconnectPeerUpdated(self.peer_update)
        iface_called_plugin.deactivate(self)    
        
    def processes_events_immediately(self):
        return True
    
    def processes_all_peer_actions(self):
        return True
    
    def process_message(self,msg,addr,_member_info):
        if self.is_db_ready():
            self.specialized_db_conn().insert_call("msg", msg, addr)
        else:
            log_warning("Statistics: DB not ready -- cannot process message")
            
    def process_lunch_call(self,msg,ip,_member_info):
        if self.is_db_ready():
            self.specialized_db_conn().insert_call("lunch", msg, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process lunch_call")
    
    def process_event(self,cmd,value,ip,_member_info,_prep):
        if self.is_db_ready():
            self.specialized_db_conn().insert_call(cmd, value, ip)
        else:
            log_warning("Statistics: DB not ready -- cannot process event")
            
    def peer_update(self, _peerID, peerInfo):        
        if self.is_db_ready():
            self.specialized_db_conn().insert_members("ip", peerInfo["name"], \
                                 peerInfo["avatar"], peerInfo["next_lunch_begin"], peerInfo["next_lunch_end"])
        else:
            log_warning("Statistics: DB not ready -- cannot store member data")

class statistics_sqlite(db_for_plugin_iface):
    version_schema = "CREATE TABLE statistics_version (commit_count INTEGER, migrate_time INTEGER)"
    messages_schema = "CREATE TABLE statistics_messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, senderIP TEXT, rtime INTEGER)"
    members_schema = "CREATE TABLE statistics_members (peerID TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    
    def init_db(self):                   
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
    
class statistics_hana(db_for_plugin_iface):
    messages_schema = "CREATE INSERT ONLY COLUMN TABLE messages ( \
            mtype VARCHAR(100), message VARCHAR(5000), sender VARCHAR(100), rtime SECONDDATE, receiver VARCHAR(100))";
    members_schema = "CREATE COLUMN TABLE members (IP VARCHAR(15), name VARCHAR(255), \
            avatar VARCHAR(255), lunch_begin VARCHAR(5), lunch_end VARCHAR(5), rtime SECONDDATE)"; 
    
    def init_db(self):
        if not self.dbConn.existsTable("members"):
            self.dbconn.execute(self.members_schema)
        if not self.dbConn.existsTable("messages"):
            self.dbConn.execute(self.messages_schema)
                
    def insert_call(self,mtype,msg,sender):
        self.dbConn.execute("INSERT INTO messages(mtype,message,sender,rtime,receiver) VALUES (?,?,?,now(),?)",mtype,msg,sender,get_settings().get_ID())          
    
    def insert_members(self,ip,name,avatar,lunch_begin,lunch_end):
        self.dbConn.execute("INSERT INTO members(IP, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,now())",ip,name,avatar,lunch_begin,lunch_end)
                
    def get_newest_members_data(self):  
        return self.dbConn.query("select * from members, (SELECT ip as maxtimeip,MAX(rtime) as maxtime FROM members GROUP BY IP) as maxtable where maxtimeip=ip and maxtime = rtime")      

