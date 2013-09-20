__all__ = ["gui_general", "lunch_default_config", "lunch_server", "iface_plugins"]

import lunch_server

def get_server():
    return lunch_server.lunch_server.get_singleton_server()

def get_lunchinator_dir():
    return get_server().main_config_dir

def get_plugin_dirs():
    return get_server().plugin_dirs