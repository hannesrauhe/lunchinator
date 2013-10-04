__all__ = ["gui_general", "lunch_settings", "lunch_server", "iface_plugins", "lunch_datathread"]

import logging, logging.handlers, os

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
            loghandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
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
    if type(string) == unicode:
        return string
    elif type(string) == str:
        print "Encountered string of type str"
        traceback.print_stack()
        return str.decode('utf-8')
    return unicode(string.toUtf8(), 'utf-8')

def _get_logger():
    return _lunchinator_logger.get_singleton_logger()

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
