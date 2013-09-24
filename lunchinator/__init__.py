__all__ = ["gui_general", "lunch_settings", "lunch_server", "iface_plugins"]

import logging, logging.handlers, os

class _lunchinator_logger:
    lunch_logger = None
     
    @classmethod
    def get_singleton_logger(cls):
        if cls.lunch_logger == None:
            main_config_dir = os.getenv("HOME")+"/.lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+"/.lunchinator"
            log_file = main_config_dir+"/lunchinator.log"
            loghandler = logging.handlers.RotatingFileHandler(log_file,'a',0,9)
            loghandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            
            cls.lunch_logger = logging.getLogger("LunchinatorLogger")
            cls.lunch_logger.addHandler(loghandler)
            
            yapsi_logger = logging.getLogger('yapsy')
            yapsi_logger.setLevel(logging.WARNING)
            yapsi_logger.addHandler(loghandler)
            
            
            loghandler.doRollover()
        return cls.lunch_logger

#initialize loggers
_lunchinator_logger.get_singleton_logger()

def _get_logger():
    return _lunchinator_logger.get_singleton_logger()

def _generate_string(*s):
    return " ".join(str(x) for x in s)

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
    return get_settings().main_config_dir

def get_plugin_dirs():
    return get_settings().plugin_dirs

#initialize settings
if get_settings().debug:
    _get_logger().setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
else:
    _get_logger().setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO)

import lunch_server

def get_server():
    return lunch_server.lunch_server.get_singleton_server()

