import logging
import os
import time

class _log_formatter (logging.Formatter):
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    def __init__(self):
        logging.Formatter.__init__(self, self.LOG_FORMAT)
        
    def formatTime(self, record, _datefmt=None):
        ct = self.converter(record.created)
        t = time.strftime(self.TIME_FORMAT, ct)
        s = "%s,%03d" % (t, record.msecs)
        return s

class _lunchinatorLogger:
    lunch_logger = None
    streamHandler = None
    logfileHandler = None
    
    @classmethod
    def initializeLogger(cls, path):
        if cls.lunch_logger == None:
            if path:
                logDir = os.path.dirname(path)
                if not os.path.exists(logDir):
                    os.makedirs(logDir)
            
            cls.lunch_logger = logging.getLogger("LunchinatorLogger")
            cls.lunch_logger.setLevel(logging.DEBUG)
            
            cls.streamHandler = logging.StreamHandler()
            cls.streamHandler.setFormatter(logging.Formatter("[%(levelname)7s] %(message)s"))
            cls.lunch_logger.addHandler(cls.streamHandler)
            
            if path:
                try:
                    cls.logfileHandler = logging.handlers.RotatingFileHandler(path, 'a', 0, 9)
                    cls.logfileHandler.setFormatter(_log_formatter())
                    cls.logfileHandler.setLevel(logging.DEBUG)
                    
                    cls.lunch_logger.addHandler(cls.logfileHandler)
                    
                    if os.path.getsize(path) > 0:
                        cls.logfileHandler.doRollover()
                except IOError:
                    cls.lunch_logger.error("Could not initialize log file.")
            
            yapsi_logger = logging.getLogger('yapsy')
            yapsi_logger.setLevel(logging.WARNING)
            yapsi_logger.addHandler(cls.logfileHandler)
            yapsi_logger.addHandler(cls.streamHandler)
    
    @classmethod
    def get(cls):
        if cls.lunch_logger is None:
            raise ValueError("Logger not initialized")
        return cls.lunch_logger
    
    @classmethod
    def setLevel(cls, newLevel):
        cls.streamHandler.setLevel(newLevel)
        if cls.logfileHandler:
            cls.logfileHandler.setLevel(newLevel)

def initializeLogger(path=None):
    _lunchinatorLogger.initializeLogger(path)
    
def getLogger():
    return _lunchinatorLogger.get()

def setLoggingLevel(newLevel):
    _lunchinatorLogger.setLevel(newLevel)
