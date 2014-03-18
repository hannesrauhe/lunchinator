from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, log_error
from yapsy.PluginManager import PluginManagerSingleton

class db_connections(iface_general_plugin):
    def __init__(self):
        super(db_connections, self).__init__()
        self.options = [(("connections","Connections"),"Standard"),
                        (("default_connection","Default Connection"),"Standard")]
        self.open_connections = {}
        self.db_props = {"Standard":{"db_type":"SQLite Connection",
                                     "sqlite_file":get_settings().get_main_config_dir()+"/statistics.sq3"}}
        self.plugin_manager = PluginManagerSingleton.get()
        
    def getProperties(self,name):
        return self.db_props[name]
          
    def getAvailableDBConnections(self):
        return [unicode(x) for x in self.options["connections"].split(";;")]    
    
    def getDBConnection(self,name=""):
        if len(name)==0:
            name = self.options["default_connection"]
        connections = self.options["connections"].split(";;")
        
        if name not in connections:
            return None
        
        if name not in self.open_connections:
            db_type = self.getProperties(name)["db_type"]
            pluginInfo = self.plugin_manager.getPluginByName(db_type, "db")
            if pluginInfo and pluginInfo.plugin_object.is_activated:
                self.open_connections[name] = pluginInfo.plugin_object.open_connection(self.getProperties(name))
            else:
                log_error("DB Connections: %s is not available or not activated"%name)
                return None
        
        return self.open_connections[name]