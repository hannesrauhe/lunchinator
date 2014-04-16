from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_server, get_settings, log_error, log_debug, log_warning
from threading import Lock

class db_connections(iface_general_plugin):
    STANDARD_PLUGIN = "SQLite Connection"
    
    def __init__(self):
        super(db_connections, self).__init__()
        self.plugin_manager = get_server().plugin_manager
        
        self.conn_properties_lock = Lock()
        self.open_connections = {}
        self.conn_properties = {}
        self.conn_plugins = {} #will be filled later (init plugin obejcts)        
            
        self.options = [(("default_connection","Default Connection",
                          self.conn_properties.keys(),
                          get_settings().set_default_db_connection),
                         get_settings().get_default_db_connection())]
        self.force_activation = True

    ''' lazy plugin loading (not to be called in __init__ - plugins might not ba activated then) '''
    def _init_plugin_objects(self):        
        if len(self.conn_plugins)==0:
            
            '''fill the only known property for now: the type of every connection
            and store the instance'''
            for conn_name in get_settings().get_available_db_connections():
                section_name = "DB Connection: "+str(conn_name)  
                plugin_type = self.STANDARD_PLUGIN                      
                plugin_type = get_settings().read_value_from_config_file(plugin_type,
                                                                         section_name, 
                                                                         "plugin_type")

                p = self.plugin_manager.getPluginByName(plugin_type, "db")
                if p and p.plugin_object.is_activated:
                    self.conn_plugins[conn_name] = p.plugin_object
                else:
                    raise Exception("DB Connection %s requires plugin of type \
                    %s which is not available"%(conn_name,plugin_type))
                p_options = p.plugin_object.options
                for k,v in p_options.items():
                    '''this takes care of the option-type'''
                    p_options[k] = get_settings().read_value_from_config_file(v,
                                                                         section_name, 
                                                                         k)
                p_options["plugin_type"]=plugin_type
                self.conn_properties_lock.acquire()
                self.conn_properties[conn_name] = p_options
                self.conn_properties_lock.release()              
                    
    def getProperties(self, conn_id):
        self._init_plugin_objects()
        
        ob = self.conn_plugins[conn_id]            
        self.conn_properties_lock.acquire()
        prop = self.conn_properties[conn_id]
        self.conn_properties_lock.release()
        assert("plugin_type" in prop)
        
        if len(prop)==1:
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
            log_debug("DB Connections: opening connection %s of type %s"%(name,props["plugin_type"]))
            self.open_connections[name] = ob.create_connection(props)
        
        return self.open_connections[name]
    
    def create_options_widget(self, parent):
        from db_connections.DbConnOptions import DbConnOptions
        
        self._init_plugin_objects()
        
        self.conn_properties_lock.acquire()
        self.conn_options_widget = DbConnOptions(parent, self.conn_properties)
        self.conn_properties_lock.release()

        return self.conn_options_widget
    
    def save_options_widget_data(self):
        new_props = self.conn_options_widget.get_connection_properties()
        self.config_file = get_settings().get_config_file()
        '''@todo Delete connections here'''

        self.conn_properties_lock.acquire()
        
        for conn_name, props in new_props.iteritems():
            section_name = "DB Connection: "+str(conn_name)
            if conn_name not in self.conn_properties:
                log_debug("DB Connection: new connection "+conn_name)
                if self.config_file.has_section(section_name):
                    log_warning("DB Connection: a section with the name %s already \
                    exists although it is supposed to be a new connection, maybe a bug..."%conn_name)
                else:
                    self.config_file.add_section(section_name)
                self.conn_properties[conn_name] = {"plugin_type": props["plugin_type"]}
            
            if props != self.conn_properties[conn_name]:
                log_debug("DB Connection: updated properties for "+conn_name)
                
                if not self.config_file.has_section(section_name):
                    self.config_file.add_section(section_name)
                    
                for o, v in props.iteritems():
                    self.config_file.set(section_name, o, unicode(v))
                self.conn_properties[conn_name] = props
                
                if conn_name in self.open_connections:
                    '''@todo: handle plugins that use this connection (not sure if 
                    necessary, will be re-opened automatically)'''
                    conn = self.open_connections.pop(conn_name)
                    conn.close()
                
        get_settings().set_available_db_connections(self.conn_properties.keys())
        self.conn_properties_lock.release()
            
        self.conn_plugins = {}
        self._init_plugin_objects()
        
        
        '''@todo release locks'''