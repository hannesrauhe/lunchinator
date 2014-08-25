from lunchinator import convert_string
from lunchinator.log.notification_handler import NotificationLogHandler
import logging
from logging.handlers import RotatingFileHandler
import os
import time
import json

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
            yapsi_logger.setLevel(getLoggingLevel('yapsy'))
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
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        if len(logger.handlers) is 0:
            # not yet initialized
            logger.setLevel(cls.getLoggingLevel(name))
            logger.addHandler(cls.streamHandler)
            if cls.logfileHandler:
                logger.addHandler(cls.logfileHandler)
            logger.addHandler(cls.notificationHandler)

        cls._loggers[name] = logger
        from lunchinator import get_notification_center
        get_notification_center().emitLoggerAdded(name)
        return logger
    
    @classmethod
    def removeLogger(cls, name):
        l = cls._loggers.pop(name, None)
        if l is not None:
            from lunchinator import get_notification_center
            get_notification_center().emitLoggerRemoved(name)
    
    @classmethod
    def setGlobalLevel(cls, newLevel):
        if newLevel == cls._globalLevel:
            return
        cls._globalLevel = newLevel
        for name, logger in cls._loggers.iteritems():
            if name not in cls._specificLevels:
                logger.setLevel(newLevel)
        from lunchinator import get_notification_center
        get_notification_center().emitLoggingLevelChanged(None, newLevel)
                
    @classmethod
    def setLoggingLevel(cls, name, newLevel):
        if not name:
            cls.setGlobalLevel(newLevel)
        else:
            logger = cls._loggers.get(name, None)
            if logger is not None:
                if newLevel is None:
                    # reset to global level
                    logger.setLevel(cls._globalLevel)
                else:
                    logger.setLevel(newLevel)
            
            if newLevel is None:
                # remove specific level
                oldLevel = cls._specificLevels.pop(name, None)
            else:
                oldLevel = cls._specificLevels.get(name, None)
                cls._specificLevels[name] = newLevel
                
            if oldLevel != newLevel:
                from lunchinator import get_notification_center
                get_notification_center().emitLoggingLevelChanged(name, newLevel)
            
    @classmethod    
    def getLoggingLevel(cls, name):
        if name and name in cls._specificLevels:
            return cls._specificLevels[name]
        return cls._globalLevel
    
    @classmethod    
    def getSpecificLoggingLevel(cls, name):
        if name and name in cls._specificLevels:
            return cls._specificLevels[name]
        return None
            
    @classmethod
    def getLoggerNames(cls):
        return list(cls._loggers.keys())
        
    @classmethod    
    def getCachedRecords(cls):
        return cls.notificationHandler.getCachedRecords()
    
    @classmethod
    def setCacheSize(cls, size):
        cls.notificationHandler.setCacheSize(size)
        
    @classmethod
    def serialize(cls):
        return json.dumps(cls._specificLevels)
    
    @classmethod
    def deserialize(cls, s):
        try:
            cls._specificLevels = json.loads(s)
            for loggerName, level in cls._specificLevels.iteritems():
                if loggerName in cls._loggers:
                    cls.setLoggingLevel(loggerName, level)
        except:
            getCoreLogger().exception("Error deserializing logging levels.")

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
    
def setLoggingLevel(loggerName, newLevel):
    _lunchinatorLogger.setLoggingLevel(loggerName, newLevel)

def getLoggingLevel(component):
    return _lunchinatorLogger.getLoggingLevel(component)

def getSpecificLoggingLevel(component):
    return _lunchinatorLogger.getSpecificLoggingLevel(component)
    
def getCachedLogRecords():
    return _lunchinatorLogger.getCachedRecords()

def setLogCacheSize(size):
    _lunchinatorLogger.setCacheSize(size)
    
def getLoggerNames():
    return _lunchinatorLogger.getLoggerNames()
    
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

def serializeLoggingLevels():
    return _lunchinatorLogger.serialize()

def deserializeLoggingLevels(s):
    _lunchinatorLogger.deserialize(s)