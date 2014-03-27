from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, log_error
from yapsy.PluginManager import PluginManagerSingleton

class db_connections(iface_general_plugin):
    STANDARD_PLUGIN = "SQLite Connection"
    
    def __init__(self):
        super(db_connections, self).__init__()
        self.plugin_manager = PluginManagerSingleton.get()
        
        self.open_connections = {}
        self._init_connection_properties()
        self.options = [(("default_connection","Default Connection",
                          self.db_names,
                          get_settings().set_default_db_connection),
                         get_settings().get_default_db_connection())]
        
    def _init_connection_properties(self):      
        self.config_file = get_settings().get_config_file()
        self.db_names = get_settings().get_available_db_connections()
        self.db_types = []
        self.db_options = []
        for dbc in self.db_names:
            section_name = "DB Connection: "+str(dbc)
            o = {}
            t = "SQLite Connection"
            if self.config_file.has_section(section_name):
                o = self.config_file.get_options(section_name)
                t = o.pop("db_type") if o.has_key("db_type") else self.STANDARD_PLUGIN
            self.db_types.append(t)
            self.db_options.append(o)
        self.db_plugins = [] #will be filled on demand
                    
    def getProperties(self,name):
        if len(self.db_plugins)==0:
            for t in self.db_types:
                p = self.plugin_manager.getPluginByName(t, "db")
                if p and p.plugin_object.is_activated:
                    self.db_plugins.append(p.plugin_object)
                else:
                    raise "DB Connection %s requires plugin of type \
                    %s which is not available or not activated"%(name,t)
                    
        conn_id = self.db_names.index(name)
        if conn_id<0:
            raise "DB Connection %s not found"%name
        ob = self.db_plugins[conn_id]
        prop = self.db_options[conn_id]
        if len(prop)==0:
            prop = ob.options
        return ob,prop
    
    def deactivate(self):
        for conn in self.open_connections.values():
            conn.close()   
        iface_general_plugin.deactivate(self)
    
    def getDBConnection(self,name=""):
        if len(name)==0:
            name = get_settings().get_default_db_connection()
        
        if name not in get_settings().get_available_db_connections():
            return None
        
        if name not in self.open_connections:
            ob, props = self.getProperties(name)
            self.open_connections[name] = ob.create_connection(props)
        
        return self.open_connections[name]
    
    '''GUI Stuff''' 
    
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QGroupBox, QComboBox, QWidget, QVBoxLayout
        from lunchinator.ComboTabWidget import ComboTabWidget
        
        available_types = []
        for dbplugin in self.plugin_manager.getPluginsOfCategory("db"):
            available_types.append(dbplugin.plugin_object)
            
        widget = QWidget(parent)
        vlayout = QVBoxLayout(widget)
        connectionsWidget = ComboTabWidget(widget)
        connectionsWidget.addTab(available_types[0].create_db_options_widget(widget), "Standard")
        vlayout.addWidget(connectionsWidget)
        
        return widget
        