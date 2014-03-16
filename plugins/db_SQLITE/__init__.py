from lunchinator.iface_db_plugin import iface_db_plugin,lunch_db
import sys,sqlite3,threading,Queue,datetime
from lunchinator import get_server, get_settings, log_debug, log_exception, log_error

 
class db_SQLITE(iface_db_plugin):  
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
        super(iface_db_plugin, self).__init__()
        self.db_type="SQLite"
        self.options=[("sqlite_file", get_settings().get_main_config_dir()+"/statistics.sq3")]
        self.members={}
        
    def open_connection(self, options):
        newconn = None
        try:
            newconn = MultiThreadSQLite(options["sqlite_file"])
        except:
            log_exception("Problem while opening DB connection in plugin %s"%(self.db_type))   
            raise
        
        try:            
            if not self.existsTable("members"):
                self.execute(self.members_schema)
            if not self.existsTable("messages"):
                self.execute(self.messages_schema)
            res = self.get_newest_members_data()
            if res:
                for e in res:
                    self.members[e[0]]=e
        except:
            newconn.close()
            log_exception("Problem after opening DB connection in plugin %s"%(self.db_type))  
            raise 
        
        return newconn
        
    def close_connection(self,conn):        
        try:            
            self._pre_close()
        except:
            log_exception("Proble mbefore closing DB connection in plugin %s"%(self.db_type))
            
        try:            
            conn.close()
        except:
            log_exception("Problem while closing DB connection in plugin %s"%(self.db_type))
        
class MultiThreadSQLite(threading.Thread,lunch_db):
    def __init__(self, db_file):
        threading.Thread.__init__(self)
        lunch_db.__init__(self)
        
        self.db=db_file
        self.description=None
        self.last_res=None
        self.reqs=Queue.Queue()
        self.open = False
        
    def run(self):
        cnx = sqlite3.connect(self.db_file) 
        cursor = cnx.cursor()
        while True:
            req, arg, res = self.reqs.get()
            if req=='--commit--': 
                cnx.commit()
            else:
                if req=='--close--': break
                cursor.execute(req, arg)
                self.description = cursor.description
                if res:
                    for rec in cursor:
                        res.put(rec)
                    res.put('--no more--')
        cnx.close()
        
    def _cursor_execute(self, req, arg=None):        
        self.last_res = Queue.Queue()
        self.reqs.put((req, arg or tuple(), self.last_res))
        
    def fetch(self):
        while True:
            rec=self.last_res.get()
            if rec=='--no more--': break
            yield rec
            
    def fetchall(self):
        return list(self.fetch())
        
    def commit(self):
        self.execute('--commit--')
    
    def _open(self):       
        self.open = True 
        self.start()
    
    def _close(self):
        self.execute('--close--')
        self.open = False
        
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):
        if not self.open:
            raise Exception("not connected to a database")
        
        if wildcards:
            log_debug(query, wildcards)
            self._cursor_execute(query, wildcards)
        else:
            log_debug(query)
            self._cursor_execute(query)
        if commit:
            self._conn().commit()
        header=[]
        if self.description:
            for d in self.description:
                header.append(d[0])
        if returnHeader:
            return header,self.fetchall()
        if returnResults:
            return self.fetchall()
        
        
    
    '''Statistics'''
    def insert_call(self,mtype,msg,sender):
        self.execute("INSERT INTO messages(mtype,message,sender,rtime) VALUES (?,?,?,strftime('%s', 'now'))",mtype,msg,sender)
    
    def insert_members(self,ip,name,avatar,lunch_begin,lunch_end):
        self.execute("INSERT INTO members(IP, name, avatar, lunch_begin, lunch_end, rtime) VALUES (?,?,?,?,?,strftime('%s', 'now'))",ip,name,avatar,lunch_begin,lunch_end)
        
    def get_newest_members_data(self):    
        return self.query("SELECT IP,name,avatar,lunch_begin,lunch_end,MAX(rtime) FROM members GROUP BY IP")
        
    def existsTable(self, tableName):
        result = self.query("select sql from sqlite_master where type = 'table' and upper(name) = '%s'" % tableName.upper())
        return result != None and len(result) > 0   
    
    '''Lunch Statistics'''
    def lastUpdateForLunchDay(self, date, tableName):
        sql="SELECT LAST_UPDATE FROM %s WHERE DATE=%s" % (self.get_table_name(tableName), self.get_formatted_date(date))
        tuples = self.query(sql)
        if tuples == None or len(tuples) == 0:
            log_debug("%s -> None" % sql)
            return None
        else:
            log_debug("%s -> %s" % (sql, tuples))
            return self.parse_result_date(tuples[0][0])
        
    def insertLunchPart(self, date, textAndAdditivesList, update, table):
        sql=None
        if update:
            sql="DELETE FROM %s WHERE DATE=%s" % (self.get_table_name(table), self.get_formatted_date(date))
            log_debug(sql)
            self.executeNoCommit(sql)
        for textAndAdditives in textAndAdditivesList:
            sql="INSERT INTO %s VALUES(%s, ?, ?, %s)" % (self.get_table_name(table), self.get_formatted_date(date), self.get_formatted_date(date.today()))
            log_debug("%s, %s, %s" % (sql, textAndAdditives[0], textAndAdditives[1]))
            self.executeNoCommit(sql, textAndAdditives[0], textAndAdditives[1])            

    def get_table_name(self, baseName):
        return "\"%s\"" % baseName    
    
    def get_formatted_date(self, aDate):
        return "DATE('%s')" % datetime.datetime.combine(aDate, datetime.time()).strftime('%Y-%m-%d')
        
    def parse_result_date(self, resultDate):
        return datetime.datetime.strptime(resultDate, '%Y-%m-%d').date()
            