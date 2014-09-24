from lunchinator.plugin import iface_plugin

''' every DB plugin consists of at least two objects:
(necessary, because multiple connections of the same type are allowed)

* the first inherits from iface_db_plugin and should handle creation of 
necessary databases/tables the lunchinator will open  connections
through this interface, so that additional tasks can be executed before opening
and after closing
it also has to tell the lunchinator which properties are necessary to open a connection

* the second one inherits from lunch_db, 
the actual connection is created and administered here,
only the execute and close function will be used from the outside

'''
from lunchinator.plugin.iface_plugins import PasswordOption
from lunchinator import get_settings, convert_raw
from __builtin__ import False

class iface_db_plugin(iface_plugin):    
    def __init__(self):
        super(iface_db_plugin, self).__init__()
        self.force_activation = True
        self.passwords = set()
        self.password_options = []
        self.connName = None
        
    ''' do not overwrite these methods '''    
    def activate(self):        
        iface_plugin.activate(self)
        self.config_file = get_settings().get_config_file()

    def deactivate(self):        
        iface_plugin.deactivate(self)            
    
    ''' Options are set differently from other plugins, since - again - multiple
    instances with different options are allowed. The DB Connections plugin handles the
    properties'''
    def has_options_widget(self):
        return False
    
    def create_db_options_widget(self, parent):
        return super(iface_db_plugin, self).create_options_widget(parent)

    ############################################

    def _hasConfigOption(self, o):
        if not self.options:
            return False
        return o in self.options
    
    def _getConfigOption(self, o):
        return self.get_option(o)
    
    def _setConfigOption(self, o, v):
        # configuration is stored via DbConnOptions
        pass
    
    def _getPasswordForOption(self, o):
        return self._getPassword("dbconn_%s.%s" % (self.connName, o))
    
    def _hasPasswordForOption(self, o):
        return o in self.password_options or super(iface_db_plugin, self)._hasPasswordForOption(o)
    
    def _setPasswordOptionValue(self, o, v):
        self.passwords[o] = v
        self.password_options.add(o)
    
    #########################################

    def getOptions(self):
        return self.options
    
    def getDefaultOptions(self):
        return self.option_defaults
        
    def storePasswordForConnection(self, connName, o, p):
        self._storePassword("dbconn_%s.%s" % (connName, o), p)
        
    def getPasswords(self):
        return self.passwords
    
    def clearPasswords(self):
        self.passwords = {}

    def setConnection(self, connName, options, password_options):
        self.connName = connName
        
        if options:
            for o, v in options.iteritems():
                self.set_option(o, v, convert=False)
        else:                
            for option, _v in self._iterOptions():
                self.reset_option(option)
            self._readOptionsFromFile()
            
        self.password_options = set(password_options)
        self.passwords = {}
    
    '''should return an object of Type lunch_db which is already open'''
    def create_connection(self, properties):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    

class lunch_db(object):              
    def __init__(self):
        self.is_open = False
        
    def isOpen(self, _logger):
        return self.is_open
        
    '''convenience calls'''    
    def execute(self, logger, query, *wildcards):
        return self._execute(logger, query, wildcards, returnResults=False, commit=True)
        
    def executeNoCommit(self, logger, query, *wildcards):
        return self._execute(logger, query, wildcards, returnResults=False, commit=False)
        
    def query(self, logger, query, *wildcards):
        return self._execute(logger, query, wildcards, returnResults=True, commit=False)
    
    def queryWithHeader(self, logger, query, *wildcards):
        return self._execute(logger, query, wildcards, returnResults=True, commit=False, returnHeader=True)
    
    '''abstract methods - basic functionality'''   
    def open(self, logger):
        ''' this method is only called by iface_db_plugin::create_connection which is implemented by yourself
        therefore this acts only as a reminder that you typically need the open function, but yours might have more parameters
        '''
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
            
    def _execute(self, logger, query, wildcards, returnResults=True, commit=False, returnHeader=False):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def existsTable(self, logger, tableName):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def insert_values(self, logger, table, *values):
        raise  NotImplementedError("%s does not implement this method"%self.db_type) 
        
