from lunchinator.logging_mutex import loggingMutex
from lunchinator import log_exception
from time import gmtime, localtime, mktime
import codecs, json, os, sys

class Messages(object):
    def __init__(self, logging):
        self._messages = []
        self._lock = loggingMutex("messages", logging=logging)
    
    def getLatest(self):
        return self._messages[0]
    
    def get(self, index):
        return self._messages[index]
    
    def getAll(self, begin=None):
        messages = []
        if not begin:  
            messages = self._messages
        else:
            for mtime, addr, msg in self._messages:                    
                if mtime >= gmtime(begin):
                    messages.append([mtime, addr, msg])
                else:
                    break
        return messages
    
    
    def initFromFile(self, path):
        messages = []
        if os.path.exists(path):
            try:
                # ensure file is not empty
                if os.stat(path).st_size > 0:
                    with codecs.open(path, 'r', 'utf-8') as f:    
                        tmp_msg = json.load(f)
                        for m in tmp_msg:
                            messages.append([localtime(m[0]), m[1], m[2]])
            except:
                log_exception("Could not read messages file %s, but it seems to exist" % (path))
        with self._lock:
            self._messages = messages
    
    def writeToFile(self, path):
        try:
            if len(self) > 0:
                with codecs.open(path, 'w', 'utf-8') as f:
                    f.truncate()
                    msg = []
                    with self._lock:
                        for m in self._messages:
                            msg.append([mktime(m[0]), m[1], m[2]])
                    json.dump(msg, f)
        except:
            log_exception("Could not write messages to %s: %s" % (path, sys.exc_info()[0])) 
            
    def insert(self, mtime, addr, msg):
        with self._lock:
            self._messages.insert(0, [mtime, addr, msg])
    
    def __item__(self, index):
        return self.get(index)
    
    def __len__(self):
        return len(self._messages)
    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)