from lunchinator.logging_mutex import loggingMutex
from lunchinator import log_exception, log_warning, log_debug, get_settings
import lunchinator
from time import localtime, mktime
import codecs, json, os, sys
from collections import deque
        
class Messages(object):
    _DB_VERSION_INITIAL = 0
    _DB_VERSION_CURRENT = _DB_VERSION_INITIAL
    
    def __init__(self, path, logging):
        self._lock = loggingMutex("messages", logging=logging)
        self._db, plugin_type = lunchinator.get_db_connection()
        
        if plugin_type != "SQLite Connection":
            log_warning("Your standard connection is not of type SQLite." + \
                "Loading messages from another type is experimental.")
            
        if not self._db.existsTable("CORE_MESSAGE_VERSION"):
            self._db.execute("CREATE TABLE CORE_MESSAGE_VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO CORE_MESSAGE_VERSION(VERSION) VALUES(?)", self._DB_VERSION_INITIAL)
            
        if not self._db.existsTable("CORE_MESSAGES"):
            self._db.execute("CREATE TABLE CORE_MESSAGES(SENDER TEXT, TIME REAL, MESSAGE TEXT)")
            self._db.execute("CREATE INDEX CORE_MESSAGE_TIME_INDEX on CORE_MESSAGES(TIME ASC)")
            self._length = 0
            self._latest = None
            self.importOld(get_settings().get_legacy_messages_file())
        else:
            self._latest = self._getLatest()
            self._length = self._getNumMessages()

    def _getDBVersion(self):
        return self._db.query("SELECT VERSION FROM CORE_MESSAGE_VERSION")[0][0]
    
    def _convertMessage(self, output):
        """Returns (Time, Sender, Message)"""
        return (localtime(output[1]), output[0], output[2])
    
    def _getFirstResult(self, result):
        if not result:
            return None
        return self._convertMessage(result[0])
    
    def _getLatest(self):
        return self._getFirstResult(self._db.query("SELECT * FROM CORE_MESSAGES WHERE ROWID = (SELECT MAX(ROWID) FROM CORE_MESSAGES)"))
    
    def _getNumMessages(self):
        return self._db.query("SELECT COUNT(*) FROM CORE_MESSAGES")[0][0]
                      
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
        # TODO: writeToFile just closes DB connection? - remove this function or rename it
        log_debug("write to file called in messages - not necessary")
#        try:
#            self._db.close()
#        except:
#            log_exception("Could not write messages to %s: %s" % (path, sys.exc_info()[0])) 
    
    def insert(self, mtime, addr, msg):
        """Insert a new message
        
        mtime -- struct_time
        addr -- peer ID
        msg -- meessage text"""
        
        seconds = mktime(mtime)
        with self._lock:
            self._db.execute("INSERT INTO CORE_MESSAGES VALUES(?, ?, ?)", addr, seconds, msg)
            self._latest = (mtime, addr, msg)
            self._length += 1

    def getBulk(self, start, length, reverse=False):
        result = self._db.query("SELECT * FROM CORE_MESSAGES LIMIT ? OFFSET ?", length, start)
        if reverse:
            return (self._convertMessage(row) for row in reversed(result))
        else:
            return (self._convertMessage(row) for row in result)
        
    def getSlidingWindowCache(self, windowSize):
        return SlidingWindowCache(self, windowSize)
        
    """ --------- INTERFACE ----------- """

    def __len__(self):
        return self._length
    
    def __getitem__(self, index):
        return self.get(index)
    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
        
    def getLatest(self):
        """Returns the latest message."""
        return self._latest
    
    def get(self, index):
        """Returns the message at a given index, in terms of DB rows.
        
        Index 0 is the oldest message in the DB."""
        if index == len(self) - 1:
            # fast access to latest message
            return self.getLatest()
        return self._getFirstResult(self._db.query("SELECT * FROM CORE_MESSAGES LIMIT 1 OFFSET ?", index))
    
    def getAll(self, begin=None):
        """Get all messages.
        
        begin -- seconds since the epoch (-> time.time())
        """
        result = []
        if begin:
            messages = self._db.query("SELECT * FROM CORE_MESSAGES WHERE TIME > ?", begin)
        else:
            messages = self._db.query("SELECT * FROM CORE_MESSAGES")

        if messages:
            for msgObj in reversed(messages):
                result.append(self._convertMessage(msgObj))
        return result
    
class SlidingWindowCache(object):
    def __init__(self, messages, windowSize):
        self._messages = messages
        self._windowSize = windowSize
        self._queue = deque(maxlen=windowSize)
        self._from = 0

    def __len__(self):
        return len(self._messages)
    
    def __getitem__(self, index):
        return self.get(index)
    
    def __enter__(self):
        return self._messages.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._messages.__exit__(aType, value, traceback)
    
    def getLatest(self):
        return self._messages.getLatest()
    
    def _inQueue(self, index):
        """0: in queue, negative: before queue, positive: after queue"""
        if index >= self._from and index < self._from + len(self._queue):
            return 0
        elif index < self._from:
            return index - self._from
        else:
            return index - self._from - len(self._queue) + 1
    
    def _reset(self, newCenter):
        self._queue.clear()
        self._from = max(0, newCenter - self._windowSize / 2)
        rows = self._messages.getBulk(self._from, self._windowSize, False)
        self._queue.extend(rows)
    
    def _moveLeft(self, newCenter, diff):
        numToFetch = self._windowSize / 2 - diff
        if numToFetch <= self._windowSize:
            if self._windowSize / 2 <= newCenter:
                self._from = newCenter - self._windowSize / 2
            else:
                # don't get negative indexes
                self._from = 0
                numToFetch -= self._windowSize / 2 - newCenter
            rows = self._messages.getBulk(self._from, numToFetch, True)
            self._queue.extendleft(rows)
        else:
            # moved too far
            self._reset(newCenter)
    
    def _moveRight(self, newCenter, diff):
        # don't fetch more than is available
        numToFetch = min(self._windowSize / 2 + diff,
                         len(self._messages) - (self._from + len(self._queue)))
        
        if numToFetch <= self._windowSize:
            rows = self._messages.getBulk(self._from + len(self._queue), numToFetch, False)
            if len(self._queue) + numToFetch > self._windowSize:
                # left bound will move right
                self._from += len(self._queue) + numToFetch - self._windowSize 
            self._queue.extend(rows)
        else:
            self._reset(newCenter)
    
    def get(self, index):
        """Returns the message at a given index."""
        if index == len(self._messages) - 1:
            # fast access to latest message
            return self._messages.getLatest()
        
        inQueue = self._inQueue(index)
        if inQueue != 0:
            if inQueue < 0:
                # move window backwards
                self._moveLeft(index, inQueue)
            else:
                self._moveRight(index, inQueue)
                
        return self._queue[index - self._from]
    
    def getAll(self, begin=None):
        return self._messages.getAll(begin)
    
if __name__ == '__main__':
    class MessagesWrapper():
        data = range(11)
        
        def __len__(self):
            return len(self.data)
        
        def getBulk(self, fromIndex, length, reverse):
            print "get from", fromIndex, " to ", fromIndex + length - 1
            if reverse:
                return (i for i in reversed(self.data[fromIndex:fromIndex + length]))
            else:
                return (i for i in self.data[fromIndex:fromIndex + length])
            
        def getLatest(self):
            return self.data[-1]
            
    cache = SlidingWindowCache(MessagesWrapper(), 10)
    print cache.get(0)
    print cache.get(9)
    
    sys.exit(0)
    for i in range(10):
        print cache.get(i)
    for i in range(10, -1, -1):
        print cache.get(i)

    print cache.get(70)
    print cache.get(50)
    print cache.get(93)
    
    for i in range(94, 100):
        print cache.get(i)
