__all__ = ["gui_general", "lunch_settings", "lunch_server", "iface_plugins"]

import os

MAIN_CONFIG_DIR = unicode(os.path.join(os.getenv("HOME"), ".lunchinator") if os.getenv("HOME") else os.path.join(os.getenv("USERPROFILE"), ".lunchinator"))

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
        from lunchinator.log import getCoreLogger
        getCoreLogger().exception("Cannnot load plugin manager: plugins are disabled")   
        
def get_peer_actions():
    from lunchinator.peer_actions import PeerActions
    return PeerActions.get()
    
def get_db_connection(logger, name=""):
    """returns tuple (connection_handle, connection_type) of the given connection"""
    
    from lunchinator.log import getCoreLogger
    if not get_settings().get_plugins_enabled():
        getCoreLogger().error("Plugins are disabled, cannot get DB connections.")
        return None, None
    
    pluginInfo = get_plugin_manager().getPluginByName("Database Settings", "general")
    if pluginInfo and pluginInfo.plugin_object.is_activated:
        return pluginInfo.plugin_object.getDBConnection(logger, name)
    getCoreLogger().error("getDBConnection: DB Connections plugin not yet loaded")
    return None, None
