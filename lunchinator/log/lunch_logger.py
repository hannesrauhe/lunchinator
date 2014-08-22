from lunchinator import convert_string
from lunchinator.log.notification_handler import NotificationLogHandler
import logging
from logging.handlers import RotatingFileHandler
import os
import time

class _UnicodeLogger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        convArgs = None
        for i, arg in enumerate(args):
            if type(arg) is str:
                if convArgs is None:
                    convArgs = list(args)
                convArgs[i] = convert_string(arg)
        return logging.Logger.makeRecord(self, name, level, fn, lno, msg, args if convArgs is None else tuple(convArgs), exc_info, func=func, extra=extra)

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

class _lunchinatorLogger(object):
    lunch_logger = None
    streamHandler = None
    logfileHandler = None
    
    @classmethod
    def initializeLogger(cls, path):
        if cls.lunch_logger is None:
            from lunchinator import get_settings
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
                    cls.logfileHandler = RotatingFileHandler(path, 'a', 0, 9)
                    cls.logfileHandler.setFormatter(_log_formatter())
                    cls.logfileHandler.setLevel(logging.DEBUG)
                    
                    cls.lunch_logger.addHandler(cls.logfileHandler)
                    
                    if os.path.getsize(path) > 0:
                        cls.logfileHandler.doRollover()
                except IOError:
                    cls.lunch_logger.error("Could not initialize log file.")
            
            cls.cacheHandler = NotificationLogHandler()
            cls.cacheHandler.setLevel(logging.DEBUG)
            cls.lunch_logger.addHandler(cls.cacheHandler)
            
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
    logging.setLoggerClass(_UnicodeLogger)
    _lunchinatorLogger.initializeLogger(path)
    
def getLogger():
    return _lunchinatorLogger.get()

def logsDebug():
    return _lunchinatorLogger.get().isEnabledFor(logging.DEBUG)

def setLoggingLevel(newLevel):
    _lunchinatorLogger.setLevel(newLevel)
    
def getLogLineTime(logLine):
    from datetime import datetime
    logLineWords = logLine.split()
    if len(logLineWords) < 2:
        return None
    possiblyLogDate = "%s %s" % (logLineWords[0], logLineWords[1])
    dateParts = possiblyLogDate.split(",")
    if len(dateParts) != 2:
        return
    
    try:
        formattedDate = ("%s,%06d" % (dateParts[0], int(dateParts[1]) * 1000))
        return datetime.strptime(formattedDate, "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        return None
    except:
        from lunchinator.log import getLogger
        getLogger().exception()
        return None
