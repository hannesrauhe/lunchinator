from lunchinator.iface_plugins import iface_database_plugin
import sys,sqlite3,threading,datetime
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
        iface_database_plugin.__init__(self)
        self.options = [(("sqlite_db_file", "SQLite DB file"),get_settings().get_main_config_dir()+"/statistics.sq3")]
        self.members={}
        self.db_type="sqlite"
        
    def _open(self):
        return sqlite3.connect(self.options["sqlite_db_file"])
        
    
    def _post_open(self):
        res = self.get_newest_members_data()
        if res:
            for e in res:
                self.members[e[0]]=e
                
    def _close(self):
        self._conn().close()   
        
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):
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
        header=[]
        if cursor.description:
            for d in cursor.description:
                header.append(d[0])
        if returnHeader:
            return header,cursor.fetchall()
        if returnResults:
            return cursor.fetchall()
            
    
    '''Maintainer'''        
    def getBugsFromDB(self,mode="open"):
        sql_cmd={}
        sql_cmd["all"]="select seconds_between(to_date('1970-1-1'),rtime) as unix_time,sender,message from messages where mtype='HELO_BUGREPORT_DESCR'"
        sql_cmd["closed"]="SELECT all_bugs_t.unix_time as unix_time ,sender,all_bugs_t.message as message from \
                            (select seconds_between(to_date('1970-1-1'),rtime) as unix_time,sender,message from messages where mtype='HELO_BUGREPORT_DESCR') as all_bugs_t,\
                            (select to_int(left(message,10)) as unix_time,trim(substr(message,11)) as ip from messages where mtype='HELO_BUGREPORT_CLOSE') as close_bugs_t\
                            where all_bugs_t.unix_time=close_bugs_t.unix_time\
                            and all_bugs_t.sender=close_bugs_t.ip"
        sql_cmd["open"]="select * from (%s) except (%s)"%(sql_cmd["all"],sql_cmd["closed"])
        return self.query(sql_cmd[mode]+" order by unix_time DESC")   
    
    
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

            