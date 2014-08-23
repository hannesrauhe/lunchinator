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
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
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
    _loggers = {} # name -> logger
    _globalLevel = logging.DEBUG
    _specificLevels = {} # name -> level
    
    @classmethod
    def initializeLogger(cls, path):
        if cls.lunch_logger is None:
            if path:
                logDir = os.path.dirname(path)
                if not os.path.exists(logDir):
                    os.makedirs(logDir)
            
            cls.streamHandler = logging.StreamHandler()
            cls.streamHandler.setFormatter(logging.Formatter("[%(levelname)7s] %(message)s"))
            
            cls.notificationHandler = NotificationLogHandler()
            cls.notificationHandler.setLevel(logging.DEBUG)
            
            logHandlerError = False
            if path:
                try:
                    cls.logfileHandler = RotatingFileHandler(path, 'a', 0, 9)
                    cls.logfileHandler.setFormatter(_log_formatter())
                    cls.logfileHandler.setLevel(logging.DEBUG)
                    
                    if os.path.getsize(path) > 0:
                        cls.logfileHandler.doRollover()
                except IOError:
                    logHandlerError = True
            
            yapsi_logger = logging.getLogger('yapsy')
            yapsi_logger.setLevel(cls._globalLevel)
            yapsi_logger.addHandler(cls.logfileHandler)
            yapsi_logger.addHandler(cls.streamHandler)
            cls._loggers['yapsy'] = yapsi_logger
            
            cls.lunch_logger = cls.newLogger(u"Core")
            if logHandlerError:
                cls.lunch_logger.error("Could not initialize log file.")
    
    @classmethod
    def getCoreLogger(cls):
        if cls.lunch_logger is None:
            raise ValueError("Logger not initialized")
        return cls.lunch_logger
    
    @classmethod
    def newLogger(cls, name):
        name = u"lunchinator." + name
        logger = logging.getLogger(name)
        logger.setLevel(cls._globalLevel)
        logger.addHandler(cls.streamHandler)
        if cls.logfileHandler:
            logger.addHandler(cls.logfileHandler)
        logger.addHandler(cls.notificationHandler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def removeLogger(cls, name):
        cls._loggers.pop(name, None)
    
    @classmethod
    def setGlobalLevel(cls, newLevel):
        cls._globalLevel = newLevel
        for name, logger in cls._loggers.iteritems():
            if name not in cls._specificLevels:
                logger.setLevel(newLevel)
                
    @classmethod
    def setSpecificLevel(cls, name, newLevel):
        logger = cls._loggers.get(name, None)
        if logger is not None:
            if newLevel is None:
                # reset to global level
                logger.setLevel(cls._globalLevel)
            else:
                logger.setLevel(newLevel)
        
        if newLevel is None:
            # remove specific level
            cls._specificLevels.pop(name, None)
        else:
            cls._specificLevels[name] = newLevel
            
    @classmethod
    def getLoggerNames(cls):
        return list(cls._loggers.keys())
        
    @classmethod    
    def getCachedRecords(cls):
        return cls.notificationHandler.getCachedRecords()
    
    @classmethod
    def setCacheSize(cls, size):
        cls.notificationHandler.setCacheSize(size)

def initializeLogger(path=None):
    logging.setLoggerClass(_UnicodeLogger)
    _lunchinatorLogger.initializeLogger(path)
    
def getCoreLogger():
    return _lunchinatorLogger.getCoreLogger()

def newLogger(name):
    return _lunchinatorLogger.newLogger(name)

def removeLogger(name):
    _lunchinatorLogger.removeLogger(name)

def setGlobalLoggingLevel(newLevel):
    _lunchinatorLogger.setGlobalLevel(newLevel)
    
def setSpecificLoggingLevel(loggerName, newLevel):
    _lunchinatorLogger.setSpecificLevel(loggerName, newLevel)
    
def getCachedLogRecords():
    return _lunchinatorLogger.getCachedRecords()

def setLogCacheSize(size):
    _lunchinatorLogger.setCacheSize(size)
    
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
        return None
