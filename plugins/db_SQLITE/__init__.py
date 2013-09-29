from lunchinator.iface_plugins import *
import sys,sqlite3
from lunchinator import get_server, get_settings, log_debug
    
class db_SQLITE(iface_database_plugin):
    def __init__(self):
        super(db_SQLITE, self).__init__()
        self.options = [(("sqlite_db_file", "SQLite DB file"),get_settings().main_config_dir+"/statistics.sq3")]
        self.members={}
        self.conn = {}
        self.db_type="sqlite"
        
    def activate(self):
        iface_database_plugin.activate(self)
        
    def deactivate(self):
        conns_to_close = self.conn.keys()
        for c in conns_to_close:
            self._close(c)
        self.conn_of_type[:] = []
        iface_database_plugin.deactivate(self)
        
    def _open(self,name):
        return sqlite3.connect(self.options["sqlite_db_file"])
        
    def _close(self,name):
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
            
            