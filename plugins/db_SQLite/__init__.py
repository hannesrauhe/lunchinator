from lunchinator.plugin import iface_db_plugin
from lunchinator import get_settings
from db_SQLite.multithreaded_sqlite import MultiThreadSQLite
import os
 
class db_SQLite(iface_db_plugin):
    def __init__(self):
        super(db_SQLite, self).__init__()
        self.options=[("sqlite_file", os.path.join(get_settings().get_main_config_dir(),"lunchinator.sq3"))]
        self.members={}
        
    def create_connection(self, connName, options):
        newconn = None
        try:
            newconn = MultiThreadSQLite(options["sqlite_file"], self, connName)
            newconn.open(self.logger)
        except:
            self.logger.exception("Problem while opening SQLite connection")   
            raise
        
        return newconn
