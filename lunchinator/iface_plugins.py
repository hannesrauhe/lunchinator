from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
from lunchinator import log_error, log_exception, convert_string
import types, sys, logging
from copy import deepcopy
from PyQt4.QtCore import Qt

class iface_plugin(IPlugin):    
    def __init__(self):
        self.options = None
        self.option_names = None
        self.option_defaults = {}
        self.option_callbacks = {}
        self.option_widgets = {}
        self.option_choice = {}
        self.hidden_options = None
        manager = PluginManagerSingleton.get()
        self.shared_dict = manager.app.shared_dict if hasattr(manager, "app") else None
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
                            self.register_option_callback(o[0], aConf)
                        elif type(aConf) in (tuple, list):
                            self.option_choice[o[0]] = aConf
                else:
                    dict_options[o] = v
                    self.option_names.append((o,o))
            self.options = dict_options
            
        self.option_defaults = deepcopy(self.options)
        self.read_options_from_file()
        return

    def deactivate(self):
        """
        Just call the parent class's method
        """
        IPlugin.deactivate(self)
        self.option_widgets = {}
    
    def get_option_names(self):
        if self.option_names == None:
            return [(aKey, aKey) for aKey in self.options.keys()]
        return self.option_names
    
    def get_option_description(self, key):
        if self.option_names != None:
            for aKey, desc in self.option_names:
                if key == aKey:
                    return desc
        return None
    
    def has_options(self):
        return self.options != None and len(self.options) > 0
    
    def convert_option(self, o, v, new_v):
        try:
            if o in self.option_choice:
                finalValue = None
                for aValue in self.option_choice[o]:
                    if new_v.upper() == aValue.upper():
                        finalValue = aValue
                        break
                if finalValue != None:
                    return finalValue
                else:
                    # keep old value
                    return self.options[o]
            elif type(v)==types.IntType:
                return int(new_v)
            elif type(v)==types.BooleanType:
                if new_v.strip().upper() in ["TRUE", "YES", "1"]:
                    return True
                else:
                    return False
            elif type(v) in (types.StringType, types.UnicodeType):
                return convert_string(new_v)
            else:
                log_error("type of value",o,v,"not supported, using default")
        except:
            log_exception("could not convert value of",o,"from config to type",type(v),"(",new_v,") using default")
    
    def read_options_from_file(self):
        if not hasattr(self, "hasConfigOption"):
            return
        if self.options:
            for o,v in self.options.iteritems():
                if self.hasConfigOption(o):
                    new_v = self.getConfigOption(o)
                    conv = self.convert_option(o, v, new_v)
                    self.options[o] = conv
        
        if self.hidden_options:
            for o,v in self.hidden_options.iteritems():
                if self.hasConfigOption(o):
                    new_v = self.getConfigOption(o)
                    conv = self.convert_option(o, v, new_v)
                    self.hidden_options[o] = conv
        
    def _displayOptionValue(self, o, v):
        e = self.option_widgets[o]
        if o in self.option_choice:
            currentIndex = 0
            if v in self.option_choice[o]:
                currentIndex = self.option_choice[o].index(v)
            e.setCurrentIndex(currentIndex)
        elif type(v)==types.IntType:
            e.setValue(v)
        elif type(v)==types.BooleanType:
            e.setCheckState(Qt.Checked if v else Qt.Unchecked)
        else:
            e.setText(v)
        
    def add_option_to_layout(self, parent, grid, i, o, v):
        from PyQt4.QtGui import QLabel, QComboBox, QSpinBox, QLineEdit, QCheckBox
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
        if not self.options or not self.is_activated:
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
    
    def has_option(self, o):
        return o in self.options
    
    def _set_option(self, o, new_v, targetDict, convert = True):
        if o not in targetDict:
            return
        v = targetDict[o]
        if convert:
            new_v = self.convert_option(o, v, new_v)
        if new_v!=v:
            if o in self.option_callbacks:
                mod_v = self.option_callbacks[o](o, new_v)
                if mod_v != None:
                    # callback returned modified value
                    new_v = mod_v 
            targetDict[o]=new_v
            self.set_option_value(o, new_v)
        self._displayOptionValue(o, new_v)
            
    def register_option_callback(self, o, callback):
        if o in self.option_callbacks:
            raise AttributeError(u"There already is a callback registered for option '%s'" % o)
        self.option_callbacks[o] = callback
    
    def set_option(self, o, new_v, convert = True):
        """
        Set option o to the new value new_v.
        If you are sure that new_v has the correct type, you can set convert = False.
        """
        self._set_option(o, new_v, self.options, convert)
        
    def set_hidden_option(self, o, new_v, convert = True):
        """
        Set hidden option o to the new value new_v.
        If you are sure that new_v has the correct type, you can set convert = False.
        """
        self._set_option(o, new_v, self.hidden_options, convert)
                
    def reset_option(self, o):
        """
        Reset an option to its default value.
        """
        if o in self.options:
            self.set_option(o, self.option_defaults[o], False)
            
    def get_option_default_value(self, o):
        """
        Returns the default value of an option.
        """
        if o in self.option_defaults:
            return self.option_defaults[o]
        return None
                
    def get_option(self, o):
        if o in self.options:
            return self.options[o]
        
    def read_data_from_widget(self, o, e):
        v = self.options[o]
        new_v = v
        if o in self.option_choice:
            new_v = self.option_choice[o][e.currentIndex()]
        elif type(v)==types.IntType:
            new_v = e.value()
        elif type(v)==types.BooleanType:
            new_v = e.checkState() == Qt.Checked
        else:
            new_v = convert_string(e.text())
        return new_v        
    
    def save_data(self):
        from PyQt4.QtCore import Qt
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            new_v = self.read_data_from_widget(o, e)
            self.set_option(o, new_v, False)
        
    def set_option_value(self, o, new_v):
        self.setConfigOption(o,str(new_v))
        
    def save_options_widget_data(self):
        self.save_data()
    
    def discard_changes(self):
        for o,_e in self.option_widgets.iteritems():
            val = self.get_option(o)
            self.set_option(o, val, convert=False)
        
    @classmethod
    def prepare_application(cls, factory):
        from PyQt4.QtGui import QApplication, QMainWindow
        from lunchinator import setLoggingLevel
        from utilities import setValidQtParent
    
        setLoggingLevel(logging.DEBUG)    
        app = QApplication(sys.argv)
        window = QMainWindow()
        
        setValidQtParent(window)
        window.setWindowTitle("Layout Example")
        window.resize(300, 300)
        window.setCentralWidget(factory(window))
        window.show()
        window.activateWindow()
        window.raise_()
        return window, app
    
    def _init_run_options_widget(self, parent):
        self.activate()
        return self.create_options_widget(parent)
    
    def run_options_widget(self):
        _window, app = iface_general_plugin.prepare_application(self._init_run_options_widget)
        sys.exit(app.exec_())
        
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
        _window, app = cls.prepare_application(factory)
        sys.exit(app.exec_())
        
    def run_in_window(self):
        _window, app = iface_gui_plugin.prepare_application(lambda window : self.create_widget(window))
        self.activate()
        sys.exit(app.exec_())
        
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass
    
