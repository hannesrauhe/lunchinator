from lunchinator.iface_plugins import iface_plugin
from lunchinator import log_exception, log_info, log_error

''' every DB plugin consists of at least two objects:
(necessary, because multiple connections of the same type are allowed)

* the first inherits from iface_db_plugin and should handle creation of 
necessary databases/tables the lunchinator will open and close connections
through this interface, so that additional tasks can be executed before opening
and after closing
it also has to tell the lunchinator which properties are necessary to open a connection

* the second one inherits from lunch_db, 
the actual connection is created and administered here,
only the execute function will be used from the outside
'''

class iface_db_plugin(iface_plugin):    
    def __init__(self):
        super(iface_db_plugin, self).__init__()
        self.db_type="Unknown"
        
    ''' do not overwrite these methods '''    
    def activate(self):        
        iface_plugin.activate(self)

    def deactivate(self):        
        iface_plugin.deactivate(self)            
    
    def create_db_options_widget(self, parent):
        return super(iface_db_plugin, self).create_db_options_widget(parent)
    
    def create_options_widget(self, parent):
        return None
        
    '''should return an object of Type lunch_db'''
    def open_connection(self, properties):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def close_connection(self):
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
            
       
        