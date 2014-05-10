from lunchinator.logging_mutex import loggingMutex
from lunchinator import log_exception
from time import localtime, mktime
import codecs, json, os, sys
from lunchinator.multithreaded_sqlite import MultiThreadSQLite

class Messages(object):
    _DB_VERSION_INITIAL = 0
    _DB_VERSION_CURRENT = _DB_VERSION_INITIAL
    
    def __init__(self, path, logging):
        self._lock = loggingMutex("messages", logging=logging)
        self._db = MultiThreadSQLite(path)
        self._db.open()
        
        if not self._db.existsTable("VERSION"):
            self._db.execute("CREATE TABLE VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO VERSION(VERSION) VALUES(?)", self._DB_VERSION_INITIAL)
            
        if not self._db.existsTable("MESSAGES"):
            self._db.execute("CREATE TABLE MESSAGES(SENDER TEXT, TIME REAL, MESSAGE TEXT)")

    def getDBVersion(self):
        return self._db.query("SELECT VERSION FROM VERSION")[0][0]
    
    def _convertMessage(self, output):
        return (localtime(output[1]), output[0], output[2])
    
    def _getFirst(self, result):
        if not result:
            return None
        return self._convertMessage(result[0])
    
    def getLatest(self):
        return self._getFirst(self._db.query("SELECT * FROM MESSAGES WHERE ROWID = (SELECT MAX(ROWID) FROM MESSAGES)"))
    
    def get(self, index):
        return self._getFirst(self._db.query("SELECT * FROM MESSAGES OFFSET ? LIMIT 1", index))
    
    def getAll(self, begin=None):
        """Get all messages.
        
        begin -- seconds since the epoch (-> time.time())
        """
        result = []
        if begin:
            messages = self._db.query("SELECT * FROM MESSAGES WHERE TIME > ?", begin)
        else:
            messages = self._db.query("SELECT * FROM MESSAGES")

        if messages:
            for msgObj in reversed(messages):
                result.append(self._convertMessage(msgObj))
        return result                    
    
    def importOld(self, path):
        if os.path.exists(path):
            try:
                # ensure file is not empty
                if os.stat(path).st_size > 0:
                    messages = []
                    with codecs.open(path, 'r', 'utf-8') as f:    
                        tmp_msg = json.load(f)
                        for m in tmp_msg:
                            messages.append((localtime(m[0]), m[1], m[2]))
                    for mtime, addr, msg in reversed(messages):
                        self.insert(mtime, addr, msg)
            except:
                log_exception("Could not read messages file %s, but it seems to exist" % (path))
    
    
    def writeToFile(self, path):
        try:
            self._db.close()
        except:
            log_exception("Could not write messages to %s: %s" % (path, sys.exc_info()[0])) 
            
    def insert(self, mtime, addr, msg):
        """Insert a new message
        
        mtime -- struct_time
        addr -- peer ID
        msg -- meessage text"""
        
        seconds = mktime(mtime)
        with self._lock:
            self._db.execute("INSERT INTO MESSAGES VALUES(?, ?, ?)", addr, seconds, msg)
    
    def __item__(self, index):
        return self.get(index)
    
    def __len__(self):
        return self._db.query("SELECT COUNT(*) FROM MESSAGES")[0][0]
    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)