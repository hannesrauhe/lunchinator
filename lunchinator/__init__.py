from datetime import datetime
__all__ = ["gui_general", "lunch_settings", "lunch_server", "iface_plugins", "lunch_datathread"]

import logging, logging.handlers, os, time

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

class _lunchinator_logger:
    lunch_logger = None
    streamHandler = None
     
    @classmethod
    def get_singleton_logger(cls):
        if cls.lunch_logger == None:
            #TODO: how do we make sure, that this is the same directory like in the lunch_settings?
            main_config_dir = os.getenv("HOME")+os.sep+".lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+os.sep+".lunchinator"
            if not os.path.exists(main_config_dir ):
                os.makedirs(main_config_dir )
            log_file = main_config_dir+os.sep+"lunchinator.log"
                
            loghandler = logging.handlers.RotatingFileHandler(log_file,'a',0,9)
            loghandler.setFormatter(_log_formatter())
            loghandler.setLevel(logging.DEBUG)
            
            cls.streamHandler = logging.StreamHandler()
            cls.streamHandler.setFormatter(logging.Formatter("[%(levelname)7s] %(message)s"))
            
            cls.lunch_logger = logging.getLogger("LunchinatorLogger")
            cls.lunch_logger.setLevel(logging.DEBUG)
            cls.lunch_logger.addHandler(loghandler)
            cls.lunch_logger.addHandler(cls.streamHandler)
            
            yapsi_logger = logging.getLogger('yapsy')
            yapsi_logger.setLevel(logging.WARNING)
            yapsi_logger.addHandler(loghandler)
            yapsi_logger.addHandler(cls.streamHandler)
            
            loghandler.doRollover()
        return cls.lunch_logger

#initialize loggers
_lunchinator_logger.get_singleton_logger()

def convert_string(string):
    import traceback
    from cStringIO import StringIO
    if type(string) == unicode:
        return string
    elif type(string) == str:
        log_warning("Encountered string of type str")
        trace = StringIO()
        traceback.print_stack(None, None, trace)
        log_warning(trace.getvalue())
        trace.close()
        return string.decode('utf-8')
    return unicode(string.toUtf8(), 'utf-8')

def _get_logger():
    return _lunchinator_logger.get_singleton_logger()

def getLogLineTime(logLine):
    logLineWords = logLine.split()
    if len(logLineWords) < 2:
        return None
    possiblyLogDate = "%s %s" % (logLineWords[0], logLineWords[1])
    dateParts = possiblyLogDate.split(",")
    if len(dateParts) != 2:
        return
    
    try:
        formattedDate = ("%s,%6d" % (dateParts[0], int(dateParts[1]) * 1000))
        return datetime.strptime(formattedDate, "%Y-%m-%d %H:%M:%S,%f")
    except:
        return None

def setLoggingLevel(newLevel):
    # ensure logger is initialized
    _get_logger()
    _lunchinator_logger.streamHandler.setLevel(newLevel)
    
def _generate_string(*s):
    return u" ".join(x if type(x) in (str, unicode) else str(x) for x in s)

def log_exception(*s):
    _get_logger().exception(_generate_string(*s))
    
def log_critical(*s):
    _get_logger().critical(_generate_string(*s))
    
def log_error(*s):
    _get_logger().error(_generate_string(*s))
    
def log_warning(*s):
    _get_logger().warn(_generate_string(*s))
    
def log_info(*s):
    _get_logger().info(_generate_string(*s))
    
def log_debug(*s):
    _get_logger().debug(_generate_string(*s))

import lunch_settings

def get_settings():
    return lunch_settings.lunch_settings.get_singleton_instance()
    
def get_lunchinator_dir():
    return get_settings().get_main_config_dir()

def get_plugin_dirs():
    return get_settings().get_plugin_dirs()

#initialize settings
get_settings().set_logging_level(get_settings().get_logging_level())

import lunch_server

def get_server():
    return lunch_server.lunch_server.get_singleton_server()
