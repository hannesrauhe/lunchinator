import threading
import Queue
import sqlite3
from iface_db_plugin import lunch_db
from lunchinator import log_debug
import datetime

class MultiThreadSQLite(threading.Thread, lunch_db):
    def __init__(self, db_file):
        threading.Thread.__init__(self)
        lunch_db.__init__(self)
        
        self.db_file=db_file
        self.results={}
        self.reqs=Queue.Queue()
        self.is_open = False
        
    def run(self):
        cnx = sqlite3.connect(self.db_file) 
        cursor = cnx.cursor()
        while True:
            req, arg, res, err, description, commit = self.reqs.get()
            if req=='--close--': 
                res.put('--no more--')
                description.put('--no more--')
                break
            try:
                cursor.execute(req, arg)
                description.put(cursor.description)
                if res:
                    for rec in cursor:
                        res.put(rec)
                    res.put('--no more--')
                if commit:
                    cnx.commit()
            except Exception, e:
                err.put(e)
                description.put('--error')
                res.put('--error--')
        cnx.close()
        
    def open(self):
        self.is_open = True 
        self.start()
    
    def close(self):
        self.execute('--close--')
        self.is_open = False
        
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):            
        if not self.is_open:
            raise Exception("not connected to a database")
        
        res = Queue.Queue()
        err = Queue.Queue()
        descr = Queue.Queue()
        if wildcards:
            log_debug(query, wildcards)
            self.reqs.put((query, wildcards, res, err, descr, commit))
        else:
            log_debug(query)
            self.reqs.put((query, tuple(), res, err, descr, commit))
            
        resultList = []
        while True:
            rec=res.get()
            if rec=='--no more--': break
            if rec=='--error--':
                raise err.get()
            resultList.append(rec)
        
        header=[]
        description = descr.get()
        if description:
            for d in description:
                header.append(d[0])
        if returnHeader:
            return header,resultList
        if returnResults:
            return resultList
        
        
    
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