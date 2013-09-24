__all__ = ["gui_general", "lunch_default_config", "lunch_server", "iface_plugins"]

import logging

def get_logger():
    return logging.getLogger("LunchinatorLogger")

def log_exception(s):
    if isinstance(s, Exception):
        get_logger().exception(s.value)
    else:
        get_logger().exception(s)
    
def log_critical(s):
    get_logger().critical(s)
    
def log_error(s):
    get_logger().error(s)
    
def log_warning(s):
    get_logger().warn(s)
    
def log_info(s):
    get_logger().info(s)
    
def log_debug(s):
    get_logger().debug(s)
    
import lunch_server

def get_server():
    return lunch_server.lunch_server.get_singleton_server()

def get_lunchinator_dir():
    return get_server().main_config_dir

def get_plugin_dirs():
    return get_server().plugin_dirs
