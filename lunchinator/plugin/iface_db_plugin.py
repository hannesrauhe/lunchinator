from lunchinator.plugin import iface_plugin
import types

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

class iface_db_plugin(iface_plugin):    
    def __init__(self):
        super(iface_db_plugin, self).__init__()
        self.conn_options={}
        self.force_activation = True
        
    ''' do not overwrite these methods '''    
    def activate(self):        
        iface_plugin.activate(self)
        self.conn_options = self.options.copy()

    def deactivate(self):        
        iface_plugin.deactivate(self)            
    
    ''' Options are set differently from other plugins, since - again - multiple
    instances with different options are allowed. The DB Connections plugin handles the
    properties'''
    def has_options_widget(self):
        return False
      
    def save_options_widget_data(self, **_kwargs):
        pass
    
    def create_db_options_widget(self, parent):
        return super(iface_db_plugin, self).create_options_widget(parent)

    def fill_options_widget(self, options):
        if not self.option_widgets:
            return
        self.conn_options.update(options)

        from PyQt4.QtCore import Qt
        for o,e in self.option_widgets.iteritems():
            v = self.conn_options[o]
            if o[0] in self.option_choice:
                currentIndex = 0
                if v in self.option_choice[o[0]]:
                    currentIndex = self.option_choice[o[0]].index(v)
                e.setCurrentIndex(currentIndex)
            elif type(v)==types.IntType:
                e.setValue(v)
            elif type(v)==types.BooleanType:
                e.setCheckState(Qt.Checked if v else Qt.Unchecked)
            else:
                e.setText(v)
        
    def get_options_from_widget(self):
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            self.conn_options[o] = self._readDataFromWidget(o, e)
        return self.conn_options
    
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
            
    def _execute(self, logger, query, wildcards, returnResults=True, commit=False, returnHeader=False):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def existsTable(self, logger, tableName):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def insert_values(self, logger, table, *values):
        raise  NotImplementedError("%s does not implement this method"%self.db_type) 
        