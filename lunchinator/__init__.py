__all__ = ["gui_general", "lunch_settings", "lunch_server", "iface_plugins"]

import sys, os
import logging, logging.handlers, time
from datetime import datetime

MAIN_CONFIG_DIR = unicode(os.path.join(os.getenv("HOME"), ".lunchinator") if os.getenv("HOME") else os.path.join(os.getenv("USERPROFILE"), ".lunchinator"))
        
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
    logfileHandler = None
     
    @classmethod
    def get_singleton_logger(cls, path=None):
        if cls.lunch_logger == None:
            if not os.path.exists(MAIN_CONFIG_DIR):
                os.makedirs(MAIN_CONFIG_DIR)
            
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
            
        return cls.lunch_logger

def initialize_logger(path=None):
    _lunchinator_logger.get_singleton_logger(path)

def convert_string(string):
    if string is None:
        return None
    if type(string) == unicode:
        return string
    elif type(string) == str:
        return string.decode('utf-8')
    return unicode(string.toUtf8(), 'utf-8')

def convert_raw(string):
    if type(string) == str:
        return string
    elif type(string) == unicode:
        return string.decode('utf-8')
    return str(string)

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
        formattedDate = ("%s,%06d" % (dateParts[0], int(dateParts[1]) * 1000))
        return datetime.strptime(formattedDate, "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        return None
    except:
        log_exception()
        return None

def setLoggingLevel(newLevel):
    # ensure logger is initialized
    _get_logger()
    _lunchinator_logger.streamHandler.setLevel(newLevel)
    if _lunchinator_logger.logfileHandler:
        _lunchinator_logger.logfileHandler.setLevel(newLevel)
    
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
    
def logs_debug():
    return _get_logger().isEnabledFor(logging.DEBUG)

from lunchinator.notification_center import NotificationCenter
def get_notification_center():
    return NotificationCenter.getSingletonInstance()

import lunch_settings

def get_settings():
    return lunch_settings.lunch_settings.get_singleton_instance()
    
def get_lunchinator_dir():
    return get_settings().get_main_config_dir()

def get_plugin_dirs():
    return get_settings().get_plugin_dirs()

import lunch_server

def get_server():
    return lunch_server.lunch_server.get_singleton_server()

def get_peers():
    return get_server().getLunchPeers()

def get_messages():
    return get_server().get_messages()

def get_plugin_manager():
    if get_settings().get_plugins_enabled():
        from yapsy.PluginManager import PluginManagerSingleton
        return PluginManagerSingleton.get()
    else:
        log_exception("Cannnot load plugin manager: plugins are disabled")   
        
def get_peer_actions():
    from lunchinator.peer_actions import PeerActions
    return PeerActions.get()
    
def get_db_connection(name=""):
    """returns tuple (connection_handle, connection_type) of the given connection"""
    
    if not get_settings().get_plugins_enabled():
        log_error("Plugins are disabled, cannot get DB connections.")
        return None, None
    
    pluginInfo = get_plugin_manager().getPluginByName("Database Settings", "general")
    if pluginInfo and pluginInfo.plugin_object.is_activated:
        return pluginInfo.plugin_object.getDBConnection(name)
    log_exception("getDBConnection: DB Connections plugin not yet loaded")
    return None, None
