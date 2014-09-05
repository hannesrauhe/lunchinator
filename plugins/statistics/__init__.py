from lunchinator.plugin import iface_called_plugin, db_for_plugin_iface
from lunchinator import get_server, get_settings, \
    get_notification_center, get_peers
from lunchinator.log import loggingFunc

class statistics(iface_called_plugin):
    def __init__(self):
        super(statistics, self).__init__()
        self.options = [((u"db_connection", u"DB Connection", [],
                          self.reconnect_db),
                         get_settings().get_default_db_connection())]
        self.add_supported_dbms("SQLite Connection", statistics_sqlite)
        self.add_supported_dbms("SAP HANA Connection", statistics_hana)
    
    def _getChoiceOptions(self, o):
        if o in (u"db_connection", u"query_db_connection"):
            return get_settings().get_available_db_connections()
        return super(statistics, self)._getChoiceOptions()
    
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
    
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        memberID = member_info[u'ID'] if member_info else ip
        if self.is_db_ready():
            mtype = "lunch" if lunch_call else "msg"
            self.specialized_db_conn().insert_message(mtype, xmsg, ip, memberID)
        else:
            self.logger.warning("Statistics: DB not ready -- cannot process message")
    
    def process_command(self, xmsg, ip, member_info, _prep):
        memberID = member_info[u'ID'] if member_info else ip
        if self.is_db_ready():
            self.specialized_db_conn().insert_command(xmsg, ip, memberID)
        else:
            self.logger.warning("Statistics: DB not ready -- cannot process event")
            
    @loggingFunc
    def peer_update(self, _peerID, peerInfo):        
        if self.is_db_ready():
            self.specialized_db_conn().insert_members("ip", peerInfo["name"], \
                                 peerInfo["avatar"], peerInfo["next_lunch_begin"], peerInfo["next_lunch_end"])
        else:
            self.logger.warning("Statistics: DB not ready -- cannot store member data")

class statistics_sqlite(db_for_plugin_iface):
    version_schema = "CREATE TABLE statistics_version (commit_count INTEGER, migrate_time INTEGER)"
    messages_schema = "CREATE TABLE statistics_messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, senderIP TEXT, rtime INTEGER, fragments INTEGER)"
    members_schema = "CREATE TABLE statistics_members (peerID TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    
    def init_db(self):                   
        if not self.dbConn.existsTable("statistics_version"):
            self.dbConn.execute(self.version_schema)
            if self.dbConn.existsTable("messages"):
                # migrate from first version
                # create tables with statistics_prefix
                self.dbConn.execute("ALTER TABLE messages RENAME TO statistics_messages")
                self.dbConn.execute("ALTER TABLE statistics_messages ADD COLUMN senderIP TEXT DEFAULT \"\" ") 
                self.dbConn.execute("UPDATE statistics_messages SET senderIP=sender WHERE senderIP=\"\"")
                self.dbConn.execute("CREATE TABLE statistics_members (peerID TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)")
                self.dbConn.execute("INSERT INTO statistics_members SELECT * FROM members") 
                self.dbConn.execute("INSERT INTO statistics_version VALUES (1300, strftime('%s', 'now'))")
        q = self.dbConn.query("SELECT max(commit_count) as version FROM statistics_version")
        if len(q) == 0 or q[0][0] < 1778:
            self.dbConn.execute("ALTER TABLE statistics_messages ADD COLUMN fragments INTEGER DEFAULT 0 ") 
            self.dbConn.execute("INSERT INTO statistics_version(commit_count, migrate_time) VALUES(?, strftime('%s', 'now'))", 1778)
            # @todo remove "HELO_" from the mtype column
        
        # in case no migration has happened create empty tables
        if not self.dbConn.existsTable("statistics_members"):
            self.dbConn.execute(self.members_schema)
        if not self.dbConn.existsTable("statistics_messages"):
            self.dbConn.execute(self.messages_schema)
        
    def insert_message(self, mtype, xmsg, senderIP, senderID):
        msg = xmsg.getPlainMessage()
        fragments = len(xmsg.getFragments())
        self.dbConn.execute("INSERT INTO statistics_messages(mtype, message, sender, senderIP, rtime, fragments) VALUES (?,?,?,?,strftime('%s', 'now'),?)",
                            mtype, msg, senderID, senderIP, fragments)
        
    def insert_command(self, xmsg, senderIP, senderID):
        mtype = xmsg.getCommand()
        msg = xmsg.getCommandPayload()
        fragments = len(xmsg.getFragments())
        self.dbConn.execute("INSERT INTO statistics_messages(mtype, message, sender, senderIP, rtime, fragments) VALUES (?,?,?,?,strftime('%s', 'now'),?)",
                            mtype, msg, senderID, senderIP, fragments)
    
    def insert_members(self, peer_id, name, avatar, lunch_begin, lunch_end):
        self.dbConn.execute("INSERT INTO statistics_members(peerID, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,strftime('%s', 'now'))", peer_id, name, avatar, lunch_begin, lunch_end)
        
    def get_newest_members_data(self):    
        return self.dbConn.query("SELECT peerID,name,avatar,lunch_begin,lunch_end,MAX(rtime) FROM statistics_members GROUP BY peerID")
    
class statistics_hana(db_for_plugin_iface):
    version_schema = "CREATE TABLE statistics_version (commit_count INTEGER, migrate_time SECONDDATE)"
    messages_schema = "CREATE INSERT ONLY COLUMN TABLE messages ( \
            mtype VARCHAR(100), message VARCHAR(5000), sender VARCHAR(100), senderIP VARCHAR(100), receiver VARCHAR(100), fragments INTEGER DEFAULT 0, rtime SECONDDATE)";
    members_schema = "CREATE COLUMN TABLE members (IP VARCHAR(15), name VARCHAR(255), \
            avatar VARCHAR(255), lunch_begin VARCHAR(5), lunch_end VARCHAR(5), rtime SECONDDATE)"; 
    
    def init_db(self):
        if not self.dbConn.existsTable("members"):
            self.dbconn.execute(self.members_schema)
        if not self.dbConn.existsTable("messages"):
            self.dbConn.execute(self.messages_schema)
        if not self.dbConn.existsTable("statistics_version"):
            # we need to migrate now
            self.dbConn.execute("ALTER TABLE testable ADD (senderIP VARCHAR(100), fragments INTEGER DEFAULT 0)")
            self.dbConn.execute(self.version_schema)
            self.dbConn.execute("INSERT INTO statistics_version(commit_count, migrate_time) VALUES(?, now())", 1778)
        
    def insert_message(self, mtype, xmsg, senderIP, senderID):
        msg = xmsg.getPlainMessage()
        fragments = len(xmsg.getFragments())
        self.dbConn.execute("INSERT INTO statistics_messages(mtype, message, sender, senderIP, receiver, fragments, rtime) VALUES (?,?,?,?,?,?,now())",
                            mtype, msg, senderID, senderIP, get_settings().get_ID(), fragments)   
             
    def insert_call(self, xmsg, senderIP, senderID):
        mtype = xmsg.getCommand()
        msg = xmsg.getCommandPayload()
        fragments = len(xmsg.getFragments())
        self.dbConn.execute("INSERT INTO statistics_messages(mtype, message, sender, senderIP, receiver, fragments, rtime) VALUES (?,?,?,?,?,?,now())",
                            mtype, msg, senderID, senderIP, get_settings().get_ID(), fragments)        
    
    def insert_members(self, ip, name, avatar, lunch_begin, lunch_end):
        self.dbConn.execute("INSERT INTO members(IP, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,now())", ip, name, avatar, lunch_begin, lunch_end)
                
    def get_newest_members_data(self):  
        return self.dbConn.query("select * from members, (SELECT ip as maxtimeip,MAX(rtime) as maxtime FROM members GROUP BY IP) as maxtable where maxtimeip=ip and maxtime = rtime")      

