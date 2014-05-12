from lunchinator.iface_plugins import iface_plugin
from lunchinator import log_exception, log_info, log_error, convert_string
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
        self.conn_options = self.options

    def deactivate(self):        
        iface_plugin.deactivate(self)            
    
    ''' Options are set differently from other plugins, since - again - multiple
    instances with different options are allowed. The DB Connections plugin handles the
    properties'''
    def create_options_widget(self, parent):
        return None  
      
    def save_options_widget_data(self):
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
        from PyQt4.QtCore import Qt
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            self.conn_options[o] = self._readDataFromWidget(o, e)
        return self.conn_options
    
    '''should return an object of Type lunch_db which is already open'''
    def create_connection(self, properties):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    

class lunch_db(object):                
    '''convenience calls'''    
    def execute(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=False, commit=True)
        
    def executeNoCommit(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=False, commit=False)
        
    def query(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=True, commit=False)
    
    def queryWithHeader(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=True, commit=False, returnHeader=True)
    
    '''abstract methods - basic functionality'''   
            
    def _execute(self, query, wildcards, returnResults=True, commit=False, returnHeader=False):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def existsTable(self, tableName):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def insert_values(self, table, *values):
        raise  NotImplementedError("%s does not implement this method"%self.db_type) 
            
            
    '''The following maybe should be moved to the other class'''
    
    '''message statistics plugin methods''' 
    def insert_call(self,mtype,msg,sender):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def get_calls(self):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def insert_members(self,ip,name,avatar,lunch_begin,lunch_end):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
        
    def get_newest_members_data(self):    
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    '''lunch statistics plugin methods'''    
    def lastUpdateForLunchDay(self, date, tableName):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
        
    def insertLunchPart(self, date, textAndAdditivesList, update, table):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    '''maintenance plugin methods'''    
    def getBugsFromDB(self,mode="open"):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
            
       
        