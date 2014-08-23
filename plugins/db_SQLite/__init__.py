from lunchinator.plugin import iface_db_plugin, lunch_db
import sys, sqlite3, threading, Queue, datetime, os
from lunchinator import get_server, get_settings
from db_SQLite.multithreaded_sqlite import MultiThreadSQLite
 
class db_SQLite(iface_db_plugin):
    VERSION_TABLE = "DB_VERSION"
    DATABASE_VERSION_EMPTY = 0
    DATABASE_VERSION_DEFAULT_STATISTICS = 1
    DATABASE_VERSION_LUNCH_STATISTICS = 2
    
    version_schema = "CREATE TABLE \"%s\" (VERSION INTEGER)" % VERSION_TABLE 
    lunch_soup_schema =    "CREATE TABLE LUNCH_SOUP    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_main_schema =    "CREATE TABLE LUNCH_MAIN    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_side_schema =    "CREATE TABLE LUNCH_SIDE    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_dessert_schema = "CREATE TABLE LUNCH_DESSERT (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)"
      
    def __init__(self):
        super(db_SQLite, self).__init__()
        self.options=[("sqlite_file", os.path.join(get_settings().get_main_config_dir(),"lunchinator.sq3"))]
        self.members={}
        
    def create_connection(self, options):
        newconn = None
        try:
            newconn = MultiThreadSQLite(options["sqlite_file"])
            newconn.open(self.logger)
        except:
            self.logger.exception("Problem while opening SQLite connection")   
            raise
        
        return newconn
