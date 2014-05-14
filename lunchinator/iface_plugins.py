from yapsy.IPlugin import IPlugin
from lunchinator import log_error, log_exception, convert_string, \
    get_notification_center
import types, sys, logging
from copy import deepcopy

class iface_plugin(IPlugin):    
    def __init__(self):
        self.options = None
        self.option_names = None
        self.option_defaults = {}
        self.option_callbacks = {}
        self.option_widgets = {}
        self.option_choice = {}
        self.hidden_options = None
        self.force_activation = False

        super(iface_plugin, self).__init__()
    
    """ Overrides from IPlugin """
    
    def activate(self):
        """
        Call the parent class's activation method
        """
        IPlugin.activate(self)
        
        self._initOptions()
        self._readOptionsFromFile()
        return

    def deactivate(self):
        """
        Just call the parent class's method
        """
        IPlugin.deactivate(self)
        self.option_widgets = {}
    
    def _initOptions(self):
        if type(self.options) == list and self.option_names == None:
            # convert new settings format to dictionary and name array
            dict_options = {}
            self.option_names = []
            for o, v in self.options:
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
                            self._registerOptionCallback(o[0], aConf)
                        elif type(aConf) in (tuple, list):
                            self.option_choice[o[0]] = aConf
                else:
                    dict_options[o] = v
                    self.option_names.append((o, o))
            self.options = dict_options
           
        self.option_defaults = []
        if self._hasOptions():
            for o, v in self._iterOptions():
                self.option_defaults.append((o, deepcopy(v)))
        
    """ Override to change options data structure """
    
    def _hasOptions(self, hidden=False):
        """Returns True if there are any options."""
        if hidden:
            return self.hidden_options != None and len(self.hidden_options) > 0
        else:
            return self.options != None and len(self.options) > 0
    
    def _hasOption(self, o, hidden=False):
        """Returns True if o is a valid option key.
        
        hidden -- if True, search hidden options. Else, search visible options."""
        if hidden:
            return o in self.hidden_options
        else:
            return o in self.options
    
    def _getOptionNames(self, forceList=True):
        """Returns a list of (option key, option description)
        
        forceList -- Return a list of (key, key) if there are no descriptions
        """
        if self.option_names == None and forceList:
            return [(aKey, aKey) for aKey in self.options.keys()]
        return self.option_names
    
    def _getOptionValue(self, o, hidden=False):
        """Get value of an option."""
        return self.hidden_options[o] if hidden else self.options[o]
    
    def _initOptionValue(self, o, v, hidden=False):
        """Initially sets the option value, read from the settings file."""
        self._setOptionValue(o, v, hidden)
            
    def _setOptionValue(self, o, v, hidden=False, **_kwargs):
        """Stores the value of the option in memory."""
        if hidden:
            self.hidden_options[o] = v
        else:
            self.options[o] = v
    
    def _iterOptions(self, hidden=False):
        """Iterates over (option key, option value)"""
        if hidden:
            return self.hidden_options.iteritems()
        else:
            return self.options.iteritems()
    
    def _callOptionCallback(self, o, new_v, **_kwargs):
        """Calls a callback method and returns the (possibly) modified value."""
        if o in self.option_callbacks:
            mod_v = self.option_callbacks[o](o, new_v)
            if mod_v != None:
                # callback returned modified value
                return mod_v
        return new_v
    
    """ Private members """
    
    def _convertOption(self, o, v, new_v):
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
                    return self._getOptionValue(o)
            elif type(v) == types.IntType:
                return int(new_v)
            elif type(v) == types.BooleanType:
                if new_v.strip().upper() in ["TRUE", "YES", "1"]:
                    return True
                else:
                    return False
            elif type(v) in (types.StringType, types.UnicodeType):
                return convert_string(new_v)
            else:
                log_error("type of value", o, v, "not supported, using default")
        except:
            log_exception("could not convert value of", o, "from config to type", type(v), "(", new_v, ") using default")

    def _readOptionsFromFile(self):
        if self.has_options():
            for o, v in self._iterOptions():
                if self._hasConfigOption(o):
                    new_v = self._getConfigOption(o)
                    conv = self._convertOption(o, v, new_v)
                    self._initOptionValue(o, conv)
        
        if self.has_options(True):
            for o, v in self._iterOptions(True):
                if self._hasConfigOption(o):
                    new_v = self._getConfigOption(o)
                    conv = self._convertOption(o, v, new_v)
                    self._initOptionValue(o, conv, True)
        
    def _addOptionToLayout(self, parent, grid, i, o, v):
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
        elif type(v) == types.IntType:
            e = QSpinBox(parent)
            e.setMinimum(0)
            e.setMaximum(1000000)
            e.setSingleStep(1)
            e.setValue(v)
        elif type(v) == types.BooleanType:
            e = QCheckBox(parent)
            e.setCheckState(Qt.Checked if v else Qt.Unchecked)
            fillHorizontal = True
        else:
            e = QLineEdit(v, parent)
            fillHorizontal = True
            
        grid.addWidget(QLabel(o[1]), i, 0, Qt.AlignRight)
        grid.addWidget(e, i, 1, Qt.AlignLeft if fillHorizontal is False else Qt.Alignment(0))
        self.option_widgets[o[0]] = e
            
    def _set_option(self, o, new_v, convert, hidden, **kwargs):
        if not self.has_option(o, hidden):
            return
        v = self._getOptionValue(o, hidden)
        if convert:
            new_v = self._convertOption(o, v, new_v)
        if new_v != v:
            new_v = self._callOptionCallback(o, new_v, **kwargs)
            new_v = self._storeOptionValue(o, new_v)
            self._setOptionValue(o, new_v, hidden, **kwargs)
        self._displayOptionValue(o, new_v)
        
    """ Protected members """
    
    def _hasConfigOption(self, o):
        """Can be used to change the option category."""
        return self.hasConfigOption(o)
    
    def _getConfigOption(self, o):
        """Can be used to change the option category."""
        return self.getConfigOption(o)
    
    def _setConfigOption(self, o, v):
        """Can be used to change the option category."""
        return self.setConfigOption(o, v)
    
    def _storeOptionValue(self, o, new_v):
        """Checks the new value, stores it and returns the value that was stored."""
        self._setConfigOption(o, str(new_v))
        return new_v
    
    def _displayOptionValue(self, o, v=None):
        """Propagates a changed setting value to the optione widget"""
        from PyQt4.QtCore import Qt
        
        if v == None:
            v = self._getOptionValue(o)
        
        if not self.option_widgets:
            # probably not initialized yet.
            return
        e = self.option_widgets[o]
        if o in self.option_choice:
            currentIndex = 0
            if v in self.option_choice[o]:
                currentIndex = self.option_choice[o].index(v)
            e.setCurrentIndex(currentIndex)
        elif type(v) == types.IntType:
            e.setValue(v)
        elif type(v) == types.BooleanType:
            e.setCheckState(Qt.Checked if v else Qt.Unchecked)
        else:
            e.setText(v)
    
    def _registerOptionCallback(self, o, callback):
        if o in self.option_callbacks:
            raise AttributeError(u"There already is a callback registered for option '%s'" % o)
        self.option_callbacks[o] = callback
        
    def _requires_restart_callback(self, _o, _new_v):
        get_notification_center().emitRestartRequired("Some changed settings require a restart")
    
    def _readDataFromWidget(self, o, e):
        from PyQt4.QtCore import Qt
        v = self._getOptionValue(o)
        new_v = v
        if o in self.option_choice:
            new_v = self.option_choice[o][e.currentIndex()]
        elif type(v) == types.IntType:
            new_v = e.value()
        elif type(v) == types.BooleanType:
            new_v = e.checkState() == Qt.Checked
        else:
            new_v = convert_string(e.text())
        return new_v      
        
    """ Public interface """
    def create_options_widget(self, parent):
        """Called from settings dialog. Override to create custom widgets."""
        from PyQt4.QtGui import QWidget, QGridLayout
        if not self.has_options() or not self.is_activated:
            return None
        optionsWidget = QWidget(parent)
        t = QGridLayout(optionsWidget)
        i = 0
        
        if self.get_option_names(False) == None:
            # add options sorted by dictionary order
            for o, v in self._iterOptions():
                self._addOptionToLayout(optionsWidget, t, i, (o, o), v)
                i += 1
        else:
            # add options sorted by specified order
            for o in self.get_option_names(False):
                self._addOptionToLayout(optionsWidget, t, i, o, self._getOptionValue(o[0]))
                i += 1
                
        t.setColumnStretch(1, 1)
        row = t.rowCount()
        t.addWidget(QWidget(optionsWidget), row, 0)
        t.setRowStretch(row, 1)
        return optionsWidget
    
    def get_option_description(self, key):
        """Returns the readable description of an option."""
        if self.get_option_names(False) != None:
            for aKey, desc in self.get_option_names(False):
                if key == aKey:
                    return desc
        return None
        
    def get_displayed_name(self):
        """Returns the displayed name of this plugin.
        
        Return None if pluginInfo.name is good enough.
        """
        return None
    
    def has_options(self, hidden=False):
        """Returns True if there are any options
        
        hidden -- It True, check if there are hidden options, else check
                  for displayed options.
        """
        return self._hasOptions(hidden)
    
    def has_option(self, o, hidden=False):
        """Returns True if o is a valid option key.
        
        hidden -- if True, search hidden options. Else, search visible options."""
        return self._hasOption(o, hidden)
    
    def get_option_names(self, forceList=True):
        """Returns a list of (option key, option description)
        
        forceList -- Return a list of (key, key) if there are no descriptions
        """
        return self._getOptionNames(forceList)
    
    def get_option(self, o):
        """Returns the value of an option.
        
        If the option does not exist, this method returns None.
        """
        if self._hasOption(o):
            return self._getOptionValue(o)
        
    def set_option(self, o, new_v, convert=True, **kwargs):
        """
        Set option o to the new value new_v.
        If you are sure that new_v has the correct type, you can set convert = False.
        """
        self._set_option(o, new_v, convert, hidden=False, **kwargs)
        
    def set_hidden_option(self, o, new_v, convert=True, **kwargs):
        """
        Set hidden option o to the new value new_v.
        If you are sure that new_v has the correct type, you can set convert = False.
        """
        self._set_option(o, new_v, convert, hidden=True, **kwargs)
                
    def reset_option(self, o):
        """
        Reset an option to its default value.
        """
        if self.has_option(o):
            self.set_option(o, self.get_option_default_value(o), False)
            
    def get_option_default_value(self, o):
        """
        Returns the default value of a visible option.
        """
        if o in self.option_defaults:
            return self.option_defaults[o]
        return None
            
    def save_options_widget_data(self, **kwargs):
        """
        Called from GUI controller when the user presses "Save" in
        the settings dialog.
        """
        if not self.option_widgets:
            return
        for o, e in self.option_widgets.iteritems():
            new_v = self._readDataFromWidget(o, e)
            self.set_option(o, new_v, False, **kwargs)
    
    def discard_changes(self):
        """
        Called from GUI controller when the user presses "Cancel" in
        the settings dialog.
        """
        for o, _e in self.option_widgets.iteritems():
            val = self.get_option(o)
            self.set_option(o, val, convert=False)
        
    def is_activation_forced(self):
        """Returns True if the plugin should be always activated.
        
        It will be loaded automatically and not appear in the plugins
        menu.
        """
        return self.force_activation
    
    """ Used for testing """
    
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
    def process_message(self, msg, ip, member_info):
        pass
        
    def process_lunch_call(self, msg, ip, member_info):
        pass
        
    def process_event(self, cmd, value, ip, member_info):
        pass 
        
class iface_gui_plugin(iface_plugin):
    def __init__(self):
        super(iface_gui_plugin, self).__init__()
        self.sortOrder = -1
        self.visible = False
        
    def create_widget(self, _parent):
        self.visible = True
        return None
    
    def destroy_widget(self):
        """Called when the widget is hidden / closed. Ensure that create_widget restores the state."""
        self.visible = False
    
    def create_menus(self, _menuBar):
        """Creates plugin specific menus and returns a list of QMenu objects"""
        return None
    
    @classmethod
    def run_standalone(cls, factory):
        _window, app = cls.prepare_application(factory)
        sys.exit(app.exec_())
        
    def run_in_window(self):
        _window, app = iface_gui_plugin.prepare_application(lambda window : self.create_widget(window))
        self.activate()
        sys.exit(app.exec_())
        
    def process_message(self, msg, ip, member_info):
        pass
        
    def process_lunch_call(self, msg, ip, member_info):
        pass
        
    def process_event(self, cmd, value, ip, member_info):
        pass
    
