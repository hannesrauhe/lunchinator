import threading
import Queue
import sqlite3
from lunchinator.plugin import lunch_db
import datetime

class MultiThreadSQLite(threading.Thread, lunch_db):
    def __init__(self, db_file):
        threading.Thread.__init__(self)
        lunch_db.__init__(self)
        
        self.db_file=db_file
        self.results={}
        self.reqs=Queue.Queue()
        
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
        
    def open(self, _logger):
        self.is_open = True 
        self.start()
    
    def close(self, logger):
        self.execute(logger, '--close--')
        self.is_open = False
        
    def _execute(self, logger, query, wildcards, returnResults=True, commit=False, returnHeader=False):            
        if not self.is_open:
            raise Exception("not connected to a database")
        
        res = Queue.Queue()
        err = Queue.Queue()
        descr = Queue.Queue()
        if wildcards:
            logger.debug("%s, %s", query, wildcards)
            self.reqs.put((query, wildcards, res, err, descr, commit))
        else:
            logger.debug(query)
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
        
    def existsTable(self, logger, tableName):
        result = self.query(logger, "select sql from sqlite_master where type = 'table' and upper(name) = '%s'" % tableName.upper())
        return result != None and len(result) > 0   
    
    '''Lunch Statistics'''
    def lastUpdateForLunchDay(self, logger, date, tableName):
        sql="SELECT LAST_UPDATE FROM %s WHERE DATE=%s" % (self.get_table_name(logger, tableName), self.get_formatted_date(logger, date))
        tuples = self.query(logger, sql)
        if tuples == None or len(tuples) == 0:
            logger.debug("%s -> None", sql)
            return None
        else:
            logger.debug("%s -> %s", sql, tuples)
            return self.parse_result_date(logger, tuples[0][0])
        
    def insertLunchPart(self, logger, date, textAndAdditivesList, update, table):
        sql=None
        if update:
            sql="DELETE FROM %s WHERE DATE=%s" % (self.get_table_name(logger, table), self.get_formatted_date(logger, date))
            logger.debug(sql)
            self.executeNoCommit(logger, sql)
        for textAndAdditives in textAndAdditivesList:
            sql="INSERT INTO %s VALUES(%s, ?, ?, %s)" % (self.get_table_name(logger, table), self.get_formatted_date(logger, date), self.get_formatted_date(logger, date.today()))
            logger.debug("%s, %s, %s", sql, textAndAdditives[0], textAndAdditives[1])
            self.executeNoCommit(logger, sql, textAndAdditives[0], textAndAdditives[1])            

    def get_table_name(self, _logger, baseName):
        return "\"%s\"" % baseName    
    
    def get_formatted_date(self, _logger, aDate):
        return "DATE('%s')" % datetime.datetime.combine(aDate, datetime.time()).strftime('%Y-%m-%d')
        
    def parse_result_date(self, _logger, resultDate):
        return datetime.datetime.strptime(resultDate, '%Y-%m-%d').date()