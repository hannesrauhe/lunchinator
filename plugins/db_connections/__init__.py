from lunchinator.plugin import iface_general_plugin
from lunchinator import get_plugin_manager, get_settings, get_notification_center
from lunchinator.logging_mutex import loggingMutex
import logging
from functools import wraps
from types import MethodType

class _LoggerWrapper(object):
    def __init__(self, obj, logger):
        self._obj = obj
        self._logger = logger
    
    def __getattr__(self, name):
        inner = getattr(self._obj, name)
        if not isinstance(inner, MethodType):
            return inner
        def loggingFunc(*args, **kwargs):
            return inner(self._logger, *args, **kwargs)
        return loggingFunc

class db_connections(iface_general_plugin):
    STANDARD_PLUGIN = "SQLite Connection"
    DEFAULT_KEYS = set(["plugin_type"])
    
    def __init__(self):
        super(db_connections, self).__init__()
        self.plugin_manager = get_plugin_manager()
        
        self.conn_properties_lock = loggingMutex("db_conn_properties", logging=get_settings().get_verbose())
        self.open_connections = {}
        self.conn_properties = {}
        self.conn_plugins = {} #will be filled later (init plugin obejcts)        
            
        self.options = [(("default_connection","Default Connection",
                          self.conn_properties.keys(),
                          get_settings().set_default_db_connection),
                         get_settings().get_default_db_connection())]
        self.force_activation = True

    ''' lazy plugin loading (not to be called in __init__ - plugins might not be activated then) '''
    def _init_plugin_objects(self):        
        if len(self.conn_plugins)==0:
            
            self.conn_properties_lock.acquire()
            '''fill the only known property for now: the type of every connection
            and store the instance'''
            try:
                for conn_name in get_settings().get_available_db_connections():
                    section_name = "DB Connection: "+str(conn_name)  
                    plugin_type = self.STANDARD_PLUGIN                      
                    plugin_type = get_settings().read_value_from_config_file(plugin_type,
                                                                             section_name, 
                                                                             "plugin_type")
    
                    p = self.plugin_manager.getPluginByName(plugin_type, "db")
                    if p != None and p.plugin_object.is_activated:
                        self.conn_plugins[conn_name] = p.plugin_object
                    else:
                        # TODO should this be a warning?
                        self.logger.error("DB Connection %s requires plugin of type "\
                        "%s which is not available. \n Delete the connection from the Settings "\
                        "or install the DB plugin again.", conn_name, plugin_type)
                        continue
                    p_options = p.plugin_object.getDefaultOptions().copy()
                    for k,v in p_options.items():
                        '''this takes care of the option-type'''
                        p_options[k] = get_settings().read_value_from_config_file(v,
                                                                                  section_name,
                                                                                  k)
                    p_options["plugin_type"]=plugin_type
                    self.conn_properties[conn_name] = p_options
            except:
                raise
            finally:
                self.conn_properties_lock.release()              
                    
    def getProperties(self, conn_id):
        self._init_plugin_objects()
        
        ob = self.conn_plugins[conn_id]            
        with self.conn_properties_lock:
            prop = self.conn_properties[conn_id]
        assert("plugin_type" in prop)
        
        if len(prop)==1:
            prop = ob.getDefaultOptions().copy()
        return ob, prop
    
    def deactivate(self):
        for name,conn in self.open_connections.iteritems():
            try:
                conn.close(self.logger)
            except:
                self.logger.exception("While deactivating: Could not close connection %s", name)   
        iface_general_plugin.deactivate(self)
    
    def getDBConnection(self, logger, name=""):        
        """returns tuple (connection_handle, connection_type) of the given connection"""
        if len(name)==0:
            name = get_settings().get_default_db_connection()
        
        if name not in get_settings().get_available_db_connections():
            return None, None
        
        ob, props = self.getProperties(name)
        if name not in self.open_connections:
            self.logger.debug("DB Connections: opening connection %s of type %s", name, props["plugin_type"])
            self.open_connections[name] = ob.create_connection(name, props)
        
        return _LoggerWrapper(self.open_connections[name], logger), props["plugin_type"]
    
    def getConnectionType(self, _logger, name=""):
        """Returns the connection type for a given connection name."""
        if not name:
            name = get_settings().get_default_db_connection()
        
        with self.conn_properties_lock:  
            if name not in self.conn_properties:
                return None
        
        _ob, props = self.getProperties(name)
        return props["plugin_type"]        
    
    def has_options_widget(self):
        return True
    
    def create_options_widget(self, parent):
        from db_connections.DbConnOptions import DbConnOptions
        
        self._init_plugin_objects()
        
        self.conn_properties_lock.acquire()
        self.conn_options_widget = DbConnOptions(parent, self.conn_properties)
        self.conn_properties_lock.release()

        return self.conn_options_widget
    
    def save_options_widget_data(self, **_kwargs):
        new_props, new_passwords = self.conn_options_widget.get_connection_properties()
        self.config_file = get_settings().get_config_file()
        '''@todo Delete connections here'''

        with self.conn_properties_lock:
            for conn_name, props in new_props.iteritems():
                passwords = new_passwords.get(conn_name, None)
                
                section_name = "DB Connection: "+str(conn_name)
                if conn_name not in self.conn_properties:
                    self.logger.debug("DB Connection: new connection %s", conn_name)
                    if self.config_file.has_section(section_name):
                        self.logger.warning("DB Connection: a section with the name %s already \
                        exists although it is supposed to be a new connection, maybe a bug...", conn_name)
                    else:
                        self.config_file.add_section(section_name)
                    self.conn_properties[conn_name] = {"plugin_type": props["plugin_type"]}
                
                if props != self.conn_properties[conn_name] or passwords:
                    self.logger.debug("DB Connection: updated properties for %s", conn_name)
                    
                    po = self.plugin_manager.getPluginByName(props["plugin_type"], "db").plugin_object
                    defaultOptions = po.getDefaultOptions()
                    
                    if not self.config_file.has_section(section_name):
                        self.config_file.add_section(section_name)
                        
                    for o, v in props.iteritems():
                        if o in self.DEFAULT_KEYS or (o in defaultOptions and v != defaultOptions[o]):
                            self.config_file.set(section_name, o, unicode(v))
                        elif self.config_file.has_option(section_name, o):
                            # don't store default values, don't store options that this connection type doesn't have
                            self.config_file.remove_option(section_name, o)
                        
                    # remove removed options from config    
                    for o in set(self.conn_properties[conn_name].keys()) - set(props.keys()):
                        if self.config_file.has_option(section_name, o):
                            self.config_file.remove_option(section_name, o)
                            
                    self.conn_properties[conn_name] = props
                    
                    # store passwords
                    for o, p in passwords.iteritems():
                        po.storePasswordForConnection(conn_name, o, p)
                    
                    if conn_name in self.open_connections:
                        conn = self.open_connections.pop(conn_name)
                        conn.close(self.logger)
                        get_notification_center().emitDBSettingChanged(conn_name)
                        get_notification_center().emitRestartRequired("DB Settings were changed - you should restart")
                    
            get_settings().set_available_db_connections(self.conn_properties.keys())
        
        self.conn_options_widget.clear_passwords()
            
        self.conn_plugins = {}
        self._init_plugin_objects()
        
        
        '''@todo release locks'''
        
    def discard_changes(self):
        self.conn_options_widget.reset_connection_properties(self.conn_properties)
