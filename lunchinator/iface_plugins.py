from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
from lunchinator import log_warning, log_error
import types

class iface_plugin(IPlugin):    
    def __init__(self):
        self.options = None
        self.option_names = None
        self.option_callbacks = {}
        self.option_widgets = {}
        self.option_choice = {}
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
                    if len(o) < 2:
                        log_error("Setting '%s' specified as tuple must contain at least 2 elements." % o[0])
                        continue
                    dict_options[o[0]] = v
                    self.option_names.append(o)
                    
                    # check for further configurations
                    iterconf = iter(o)
                    next(iterconf)
                    next(iterconf)
                    for aConf in iterconf:
                        # can be callback or choice
                        if callable(aConf):
                            self.option_callbacks[o[0]] = aConf
                        elif type(aConf) in (tuple, list):
                            self.option_choice[o[0]] = aConf
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
                    if o in self.option_choice:
                        self.options[o] = new_v
                        if not new_v in self.option_choice[0]:
                            #illegal value - use first
                            self.options[o] = self.option_choice[0][0]
                        else:
                            self.options[o] = new_v
                    elif type(v)==types.IntType:
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
        
    def add_option_to_layout(self, parent, grid, i, o, v):
        from PyQt4.QtGui import QLabel, QComboBox, QSpinBox, QLineEdit, QCheckBox
        from PyQt4.QtCore import Qt
        e = ""
        fillHorizontal = False
        if o[0] in self.option_choice:
            e = QComboBox(parent)
            for aString in self.option_choice[o[0]]:
                e.addItem(aString)
            currentIndex = 0
            if v in self.option_choice[o[0]]:
                currentIndex = self.option_choice[o[0]].index(v)
            e.setCurrentIndex(currentIndex)
        elif type(v)==types.IntType:
            e = QSpinBox(parent)
            e.setMinimum(0)
            e.setMaximum(1000000)
            e.setSingleStep(1)
            e.setValue(v)
        elif type(v)==types.BooleanType:
            e = QCheckBox(parent)
            e.setCheckState(Qt.Checked if v else Qt.Unchecked)
            fillHorizontal = True
        else:
            e = QLineEdit(v, parent)
            fillHorizontal = True
            
        grid.addWidget(QLabel(o[1]), i, 0, Qt.AlignRight)
        grid.addWidget(e, i, 1, Qt.AlignLeft if fillHorizontal is False else Qt.Alignment(0))
        self.option_widgets[o[0]]=e
        
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QWidget, QGridLayout
        if not self.options:
            return None
        optionsWidget = QWidget(parent)
        t = QGridLayout(optionsWidget)
        i=0
        
        if self.option_names == None:
            # add options sorted by dictionary order
            for o,v in self.options.iteritems():
                self.add_option_to_layout(optionsWidget, t, i, (o,o), v)
                i+=1
        else:
            # add options sorted by specified order
            for o in self.option_names:
                self.add_option_to_layout(optionsWidget, t, i, o, self.options[o[0]])
                i+=1
                
        t.setColumnStretch(1, 1)
        row = t.rowCount()
        t.addWidget(QWidget(optionsWidget), row, 0)
        t.setRowStretch(row, 1)
        return optionsWidget
    
    def save_data(self, set_value):
        from PyQt4.QtCore import Qt
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            v = self.options[o]
            new_v = v
            if o in self.option_choice:
                new_v = self.option_choice[o][e.currentIndex()]
            elif type(v)==types.IntType:
                new_v = e.value()
            elif type(v)==types.BooleanType:
                new_v = e.checkState() == Qt.Checked
            else:
                new_v = str(e.text().toUtf8())
            if new_v!=v:
                self.options[o]=new_v
                set_value(o, new_v)
                if o in self.option_callbacks:
                    self.option_callbacks[o](o, new_v)
        self.discard_options_widget_data()
        
    def save_options_widget_data(self):
        self.save_data(lambda o, new_v: self.setConfigOption(o,str(new_v)))
        self.discard_options_widget_data()
    
    def discard_options_widget_data(self):
        self.option_widgets = {}
        
class iface_general_plugin(iface_plugin): 
    pass

class iface_called_plugin(iface_plugin): 
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass 
        
class iface_gui_plugin(iface_plugin):
    def __init__(self):
        super(iface_gui_plugin, self).__init__()
        self.sortOrder = -1
        self.visible = False
        
    def create_widget(self, _parent):
        self.visible = True
        return None
    
    """Called when the widget is hidden / closed. Ensure that create_widget restores the state."""
    def destroy_widget(self):
        self.visible = False
    
    def add_menu(self,menu):
        pass    
    
    @classmethod
    def run_standalone(cls, factory):
        from PyQt4.QtGui import QApplication, QMainWindow
        import sys
        
        app = QApplication(sys.argv)
        window = QMainWindow()
        window.setWindowTitle("Layout Example")
        window.resize(300, 300)
        window.setCentralWidget(factory.create_widget(window))
        window.show()
    
        sys.exit(app.exec_())
        
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
        self.db_type="Unknown"
    
    def activate(self):
        iface_plugin.activate(self)
        try:
            self._connection = self._open()
        except:
            log_error("Problem while opening DB connection in plugin %s"%(self.db_type))
            raise

    def deactivate(self):
        try:
            self._close()
        except:
            log_error("Problem while closing DB connection in plugin %s"%(self.db_type))
            raise
        iface_plugin.deactivate(self)
        
    def _conn(self):
        return self._connection
        
    def commit(self):
        if self._conn():
            self._conn().commit()
        #raise  NotImplementedError("%s does not implement this method"%self.db_type)
    
    '''abstract methods - basic functionality'''
    def _open(self):
        raise  NotImplementedError("%s does not implement the open method"%self.db_type)
    
    def _close(self):
        raise  NotImplementedError("%s does not implement the close method"%self.db_type)
            
    def _execute(self, query, wildcards, returnResults=True, commit=False):
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
    
