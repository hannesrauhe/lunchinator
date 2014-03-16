from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, log_error
from yapsy.PluginManager import PluginManagerSingleton

class db_connections(iface_general_plugin):
    def __init__(self):
        super(db_connections, self).__init__()
        self.options = [(("connections","Connections"),"Standard"),
                        (("default_connection","Default Connection"),"Standard")]
          
    def getAvailableDBConnections(self):
        return self.options["connections"].split(";;")
    
    '''
    def getDBConnection(self):
        if db_name in [None,"","auto"]:
            db_name = get_settings().get_default_db_connection()
            
        if db_name not in [None,"","auto"]:
            pluginInfo = self.plugin_manager.getPluginByName(db_name, "db")
            if pluginInfo and pluginInfo.plugin_object.is_activated:
                return pluginInfo.plugin_object
            log_error("No DB connection for %s available, falling back to default"%db_name)
        
        for pluginInfo in self.plugin_manager.getPluginsOfCategory("db"):
            if pluginInfo.plugin_object.is_activated:
                return pluginInfo.plugin_object
        log_error("No DB Connection available - activate a db plugin and check settings")
        return None
    '''