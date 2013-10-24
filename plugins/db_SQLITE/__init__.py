from lunchinator.iface_plugins import iface_database_plugin
import sys,sqlite3,threading,Queue,datetime
from lunchinator import get_server, get_settings, log_debug

class MultiThreadSQLite(threading.Thread):
    def __init__(self, db):
        super(MultiThreadSQLite, self).__init__()
        self.db=db
        self.description=None
        self.last_res=None
        self.reqs=Queue.Queue()
        self.start()
    def run(self):
        cnx = sqlite3.connect(self.db) 
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
    def execute(self, req, arg=None):
        self.last_res = Queue.Queue()
        self.reqs.put((req, arg or tuple(), self.last_res))
    def fetch(self):
        while True:
            rec=self.last_res.get()
            if rec=='--no more--': break
            yield rec
    def fetchall(self):
        return list(self.fetch())
    def close(self):
        self.execute('--close--')
    def commit(self):
        self.execute('--commit--')
        
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
        iface_database_plugin.__init__(self)
        self.options = [(("sqlite_db_file", "SQLite DB file",self._restart_connection),get_settings().get_main_config_dir()+"/statistics.sq3")]
        self.members={}
        self.db_type="sqlite"
        
    def _open(self):
        return MultiThreadSQLite(self.options["sqlite_db_file"])
    
    def _post_open(self):
        if not self.existsTable("members"):
            self.execute(self.members_schema)
        if not self.existsTable("messages"):
            self.execute(self.messages_schema)
        res = self.get_newest_members_data()
        if res:
            for e in res:
                self.members[e[0]]=e
                
    def _close(self):
        self._conn().close()   
        
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):
        if not self._conn():
            raise Exception("not connected to a database")
        
        cursor = self._conn()#.cursor()
        if wildcards:
            log_debug(query, wildcards)
            cursor.execute(query, wildcards)
        else:
            log_debug(query)
            cursor.execute(query)
        if commit:
            self._conn().commit()
        header=[]
        if cursor.description:
            for d in cursor.description:
                header.append(d[0])
        if returnHeader:
            return header,cursor.fetchall()
        if returnResults:
            return cursor.fetchall()
    
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

            