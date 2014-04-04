from lunchinator.iface_db_plugin import iface_db_plugin, lunch_db
import sys, os, datetime
from lunchinator import get_server, get_settings, log_debug, log_exception, log_error

 
class db_trace(iface_db_plugin):        
    def __init__(self):
        super(db_trace, self).__init__()
        self.options=[("trace_file", os.path.join(get_settings().get_main_config_dir(),"trace.sql"))]
        
    def create_connection(self, options):
        newconn = None
        try:
            newconn = lunchSQLTrace(options["trace_file"])
            newconn.open()
        except:
            log_exception("DB trace plugin: Problem while opening trace file " + options["trace_file"])   
            raise
        
        return newconn
            
class lunchSQLTrace(lunch_db):
    def __init__(self, trace_file):
        lunch_db.__init__(self)
        
        self.trace_file=trace_file
        self.is_open = False
        self.file_handle = None
        
    def open(self):       
        self.is_open = True 
        self.file_handle = open(self.trace_file, 'w')
    
    def close(self):
        self.is_open = False
        self.file_handle.close()
        
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):            
        if not self.is_open:
            raise Exception("no open trace file")
        
        '''@todo UTF-8'''
        self.file_handle.write( query + "\n" ) 
        self.file_handle.write( str(wildcards) + "\n")
        
    
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
            