from lunchinator.iface_plugins import iface_database_plugin
import sys,sqlite3,threading
from lunchinator import get_server, get_settings, log_debug

class db_SQLITE(iface_database_plugin):    
    VERSION_TABLE = "DB_VERSION"
    DATABASE_VERSION_EMPTY = 0
    DATABASE_VERSION_DEFAULT_STATISTICS = 1
    DATABASE_VERSION_LUNCH_STATISTICS = 2
    
    version_schema = "CREATE TABLE \"%s\" (VERSION INTEGER)" % VERSION_TABLE 
    messages_schema = "CREATE TABLE messages (m_id INTEGER PRIMARY KEY AUTOINCREMENT, \
            mtype TEXT, message TEXT, sender TEXT, rtime INTEGER)"
    members_schema = "CREATE TABLE members (IP TEXT, name TEXT, avatar TEXT, lunch_begin TEXT, lunch_end TEXT, rtime INTEGER)"
    lunch_soup_schema =    "CREATE TABLE LUNCH_SOUP    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_main_schema =    "CREATE TABLE LUNCH_MAIN    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_side_schema =    "CREATE TABLE LUNCH_SIDE    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_dessert_schema = "CREATE TABLE LUNCH_DESSERT (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)"
    
    def __init__(self):
        super(db_SQLITE, self).__init__()
        self.options = [(("sqlite_db_file", "SQLite DB file"),get_settings().get_main_config_dir()+"/statistics.sq3")]
        self.members={}
        self.db_type="sqlite"
        
    def activate(self):
        iface_database_plugin.activate(self)
        
    def deactivate(self):
        iface_database_plugin.deactivate(self)
        
    def _open(self):
        return sqlite3.connect(self.options["sqlite_db_file"])
        
    def _close(self):
        self._conn().close()   
        
    def _execute(self, query, wildcards, returnResults=True, commit=False):
        if not self._conn():
            raise Exception("not connected to a database")
        
        cursor = self._conn().cursor()
        if wildcards:
            log_debug(query, wildcards)
            cursor.execute(query, wildcards)
        else:
            log_debug(query)
            cursor.execute(query)
        if commit:
            self._conn().commit()
        if returnResults:
            return cursor.fetchall()
            
            