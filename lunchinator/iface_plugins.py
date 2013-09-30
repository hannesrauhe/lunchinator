from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
from lunchinator import log_warning, log_error, log_exception
import types

class iface_plugin(IPlugin):    
    def __init__(self):
        self.options = None
        self.option_names = None
        self.option_widgets = {}
        manager = PluginManagerSingleton.get()
        self.shared_dict = manager.app.shared_dict
        super(iface_plugin, self).__init__()
    
    def activate(self):
        """
        Call the parent class's activation method
        """
        IPlugin.activate(self)
        
        if type(self.options) == list and self.option_names == None:
            # convert new settings format to dictionary and name array
            dict_options = {}
            self.option_names = []
            for o,v in self.options:
                if type(o) in (tuple, list):
                    dict_options[o[0]] = v
                    self.option_names.append(o)
                else:
                    dict_options[o] = v
                    self.option_names.append((o,o))
            self.options = dict_options
        self.read_options_from_file()
        return

    def deactivate(self):
        """
        Just call the parent class's method
        """
        IPlugin.deactivate(self)
        
    def read_options_from_file(self):
        if not self.options:
            return
        for o,v in self.options.iteritems():
            if self.hasConfigOption(o):
                new_v = self.getConfigOption(o)
                try:
                    if type(v)==types.IntType:
                        self.options[o] = int(new_v)
                    elif type(v)==types.BooleanType:
                        if new_v.strip().upper() in ["TRUE", "YES", "1"]:
                            self.options[o] = True
                        else:
                            self.options[o] = False
                    elif type(v)==types.StringType:
                        self.options[o] = new_v
                    else:
                        log_error("type of value",o,v,"not supported, using default")
                except:
                    log_error("could not convert value of",o,"from config to type",type(v),"(",new_v,") using default")
        
    def add_option_to_widget(self, t, i, o, v):
        import gtk
        e = ""
        if type(v)==types.IntType:
            adjustment = gtk.Adjustment(value=v, lower=0, upper=1000000, step_incr=1, page_incr=0, page_size=0)
            e = gtk.SpinButton(adjustment)
        elif type(v)==types.BooleanType:
            e = gtk.CheckButton()
            e.set_active(v)
        else:
            e = gtk.Entry()
            e.set_text(v)
        rAlign = gtk.Alignment(1, 0.5, 0, 0)
        rAlign.add(gtk.Label(o[1]))
        t.attach(rAlign,0,1,i,i+1)
        t.attach(e,1,2,i,i+1)
        self.option_widgets[o[0]]=e
        
    def create_options_widget(self):
        import gtk
        if not self.options:
            return None
        t = gtk.Table(len(self.options),2,False)
        t.set_col_spacing(0, 5)
        i=0
        
        if self.option_names == None:
            # add options sorted by dictionary order
            for o,v in self.options.iteritems():
                self.add_option_to_widget(t, i, (o,o), v)
                i+=1
        else:
            # add options sorted by specified order
            for o in self.option_names:
                self.add_option_to_widget(t, i, o, self.options[o[0]])
                i+=1
                
        return t
    
    def save_options_widget_data(self):
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            v = self.options[o]
            new_v = v
            if type(v)==types.IntType:
                new_v = e.get_value_as_int()
            elif type(v)==types.BooleanType:
                new_v = e.get_active()
            else:
                new_v = e.get_text()
            if new_v!=v:
                self.options[o]=new_v
                self.setConfigOption(o,str(new_v))
        self.discard_options_widget_data()
    
    def discard_options_widget_data(self):
        self.option_widgets = {}
        
class iface_general_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's activation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)

class iface_gui_plugin(iface_plugin):
    def __init__(self):
        super(iface_gui_plugin, self).__init__()
        self.sortOrder = -1
        self.visible = False
    
    def activate(self):
        """
        Call the parent class's activation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
        
    def read_options_from_file(self):
        super(iface_gui_plugin, self).read_options_from_file()
        
        if self.hasConfigOption("sort_order"):
            new_v = self.getConfigOption("sort_order")
            try:
                self.sortOrder = int(new_v)
            except:
                log_warning("could not read sort order configuration")
        
    def save_sort_order(self):
        self.setConfigOption("sort_order",str(self.sortOrder))
        
    def create_widget(self):
        self.visible = True
        return None
    
    """Called when the widget is hidden / closed. Ensure that create_widget restores the state."""
    def destroy_widget(self):
        self.visible = False
    
    def add_menu(self,menu):
        pass    
        
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass

class iface_called_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's activation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass
    

class iface_database_plugin(iface_plugin):
    #connection_names = {}
    
    def __init__(self):
        super(iface_database_plugin, self).__init__()
        self._connections = {}
        self.connection_options = {}
        self.db_type="Unknown"
        self.default_connection_name = "Unkown_default"
        self.active_connection=""
    
    def activate(self):
        iface_plugin.activate(self)
        self.default_connection_name = self.db_type+"_default"
        
        #TODO: initialize connection_options from config_file        
        #TODO: do this for every connection saved in config
        av_conn = self.default_connection_name
        self.create_connection(av_conn)
        
        self.active_connection=self.default_connection_name

    def deactivate(self):
        for c in self.get_connections():
            self.switch_connection(c)
            self._close()
        iface_plugin.deactivate(self)
        
    def get_connections(self):
        return self._connections.keys()           
        
    def create_connection(self,conn_name):
        if self._connections.has_key(conn_name):
            raise Exception("Cannot create connection with name %s - it already exists in plugin %s"%(conn_name,self.db_type))    
    
        #TODO: initialize options from config or use default
        try:
            self._connections[conn_name] = self._open()
        except:
            log_error("Problem while opening DB connection %s in plugin %s"%(conn_name,self.db_type))
            raise
            
    def switch_connection(self,conn_name):
        if not self._connections.has_key(conn_name):
            raise Exception("Cannot switch to connection with name %s - it does not exists in plugin %s"%(conn_name,self.db_type))
        
        #TODO: switch options
        self.active_connection = conn_name
        
    def _conn(self,con_name=None):
        if con_name == None:
            con_name = self.active_connection
        if self._connections.has_key(con_name):
            return self._connections[con_name]
        else:
            raise Exception("No connection with name %s available in %s plugin"%(con_name,self.db_type))
    
    '''abstract methods - basic functionality'''
    def _open(self):
        raise  NotImplementedError("%s does not implement the open method"%self.db_type)
    
    def _close(self):
        raise  NotImplementedError("%s does not implement the close method"%self.db_type)
            
    def _execute(self, query, wildcards, returnResults=True, commit=False):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
        
    def commit(self):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def existsTable(self, tableName):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    def insert_values(self, table, *values):
        raise  NotImplementedError("%s does not implement this method"%self.db_type)
            
            
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
        
    '''convenience calls'''    
    def execute(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=False, commit=True)
        
    def executeNoCommit(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=False, commit=False)
        
    def query(self, query, *wildcards):
        return self._execute(query, wildcards, returnResults=True, commit=False)
    