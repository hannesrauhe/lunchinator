from yapsy.IPlugin import IPlugin
from lunchinator import convert_string, \
    get_notification_center, get_db_connection, get_connection_type, convert_raw
from lunchinator.log import loggingFunc, newLogger, removeLogger
from lunchinator.utilities import getPlatform, PLATFORM_MAC

import types, sys, logging, threading
from copy import deepcopy

class PasswordOption(object):
    pass

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
        self.plugin_name = None
        self._autoDBConnectionOption = False
        
        self._supported_dbms = {} #mapping from db plugin type to db_for_plugin_iface subclasses
        self._specialized_db_conn = None
        self._specialized_db_connect_lock = threading.Lock()

        super(iface_plugin, self).__init__()
    
    def setPluginName(self, pluginName):
        self.plugin_name = pluginName
    
    """ Overrides from IPlugin """
    
    def activate(self):
        """
        Call the parent class's activation method
        """
        IPlugin.activate(self)
        
        self.logger = newLogger(self.plugin_name)
        self._initOptions()
        self._readOptionsFromFile()
        if len(self._supported_dbms)>0:
            get_notification_center().connectDBSettingChanged(self.connect_to_db)
            self.connect_to_db()
        return

    def deactivate(self):
        """
        Just call the parent class's method
        """
        if len(self._supported_dbms)>0:
            get_notification_center().disconnectDBSettingChanged(self.connect_to_db)
        self.option_widgets = {}
        removeLogger(self.plugin_name)
        IPlugin.deactivate(self)
    
    def _initOptions(self):
        if type(self.options) == list and self.option_names == None:
            # convert new settings format to dictionary and name array
            dict_options = {}
            self.option_names = []
            for o, v in self.options:
                if type(o) in (tuple, list):
                    if len(o) < 2:
                        self.logger.error("Setting '%s' specified as tuple must contain at least 2 elements.", o[0])
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
           
        if self._supported_dbms and (self.options is None or not u"db_connection" in self.options):
            from lunchinator import get_settings
            # add db connection option
            self._autoDBConnectionOption = True
            if self.options is None:
                self.options = {}
                self.option_names = []
            self.options[u"db_connection"] = get_settings().get_default_db_connection()
            self.option_names.insert(0, (u"db_connection", u"Database Connection"))
            self._registerOptionCallback(u"db_connection", self.reconnect_db)
           
        self.option_defaults = []
        if self._hasOptions():
            for o, v in self._iterOptions():
                self.option_defaults.append((o, deepcopy(v)))
        
    def __initKeyring(self):
        import keyring
        if getPlatform() == PLATFORM_MAC:
            from keyring.backends.OS_X import Keyring
            if keyring.get_keyring() is None:
                keyring.set_keyring(Keyring())
        
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
        v = self.hidden_options[o] if hidden else self.options[o]
        if False:#v is PasswordOption:
            try:
                import keyring
                self.__initKeyring()
                return keyring.get_password("Lunchinator", "%s.%s" % (self.plugin_name, o))
            except:
                self.logger.exception("Error reading password.")
                return None
        return v
    
    def _initOptionValue(self, o, v, hidden=False):
        """Initially sets the option value, read from the settings file."""
        self._setOptionValue(o, v, hidden)
            
    def _setOptionValue(self, o, v, hidden=False, **_kwargs):
        """Stores the value of the option in memory."""
        options = self.hidden_options if hidden else self.options
        curVal = options[o]
        if curVal is PasswordOption:
            # passwords are not stored in options dict
            try:
                import keyring
                self.__initKeyring()
                keyring.set_password("Lunchinator", "%s.%s" % (self.plugin_name, o), convert_raw(v))
            except:
                self.logger.exception("Error storing password.")
        else:
            options[o] = v
    
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
    
    def _getChoiceOptions(self, o):
        """Called when initializing or updating a choice option"""
        if self._autoDBConnectionOption and o == u"db_connection":
            return self.get_supported_connections()
        return self.option_choice.get(o, None)
    
    """ Private members """
    
    def _convertOption(self, o, v, new_v):
        try:
            choiceOptions = self.option_choice.get(o, None)
            if choiceOptions is not None:
                if not choiceOptions:
                    choiceOptions = self._getChoiceOptions(o)
                finalValue = None
                for aValue in choiceOptions:
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
                self.logger.error("type of value %s %s not supported, using default", o, v)
        except:
            self.logger.exception("could not convert value of %s from config to type %s (%s) using default", o, type(v), new_v)

    def _readOptionsFromFile(self):
        for hidden in (False, True):
            if self.has_options(hidden):
                for o, v in self._iterOptions(hidden):
                    if v is PasswordOption:
                        continue
                    if self._hasConfigOption(o):
                        new_v = self._getConfigOption(o)
                        conv = self._convertOption(o, v, new_v)
                        self._initOptionValue(o, conv, hidden)
        
    def _initChoiceOption(self, optionKey, comboBox, choiceOptions, currentValue):
        comboBox.clear()
        for aString in choiceOptions:
            comboBox.addItem(aString)
        currentIndex = 0
        if currentValue in choiceOptions:
            currentIndex = choiceOptions.index(currentValue)
        comboBox.setCurrentIndex(currentIndex)
        self.option_choice[optionKey] = choiceOptions
        
    def _addOptionToLayout(self, parent, grid, i, o, v):
        from PyQt4.QtGui import QLabel, QComboBox, QSpinBox, QLineEdit, QCheckBox
        from PyQt4.QtCore import Qt
        from lunchinator.gui_elements.password_edit import PasswordEdit
        e = ""
        fillHorizontal = False
        choiceOptions = self._getChoiceOptions(o[0])
        if choiceOptions is not None:
            e = QComboBox(parent)
            self._initChoiceOption(o[0], e, choiceOptions, v)
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
        elif v is PasswordOption:
            e = PasswordEdit(parent)
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
        if v is PasswordOption:
            convert = False
        if convert:
            new_v = self._convertOption(o, v, new_v)
        if new_v != v:
            new_v = self._callOptionCallback(o, new_v, **kwargs)
            if v is not PasswordOption:
                new_v = self._storeOptionValue(o, new_v)
            self._setOptionValue(o, new_v, hidden, **kwargs)
        if not hidden:
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
    
    def _setValueToWidget(self, v, e, choiceOptions=None):
        from PyQt4.QtCore import Qt
        if choiceOptions is not None:
            currentIndex = 0
            if v in choiceOptions:
                currentIndex = choiceOptions.index(v)
            e.setCurrentIndex(currentIndex)
        elif type(v) == types.IntType:
            e.setValue(v)
        elif type(v) == types.BooleanType:
            e.setCheckState(Qt.Checked if v else Qt.Unchecked)
        elif v is PasswordOption:
            e.reset()
        else:
            e.setText(v)
    
    def _displayOptionValue(self, o, v=None):
        """Propagates a changed setting value to the options widget"""
        if v == None:
            v = self._getOptionValue(o)
        
        if not self.option_widgets:
            # probably not initialized yet.
            return
        e = self.option_widgets[o]
        choiceOptions = self.option_choice.get(o, None)
        self._setValueToWidget(v, e, choiceOptions)
    
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
        choiceOptions = self.option_choice.get(o, None)
        if choiceOptions is not None:
            new_v = choiceOptions[e.currentIndex()]
        elif type(v) == types.IntType:
            new_v = e.value()
        elif type(v) == types.BooleanType:
            new_v = e.checkState() == Qt.Checked
        elif v is PasswordOption:
            if e.isModified():
                newPassword = convert_raw(e.text())
                e.reset()
                return newPassword
            else:
                return PasswordOption
        else:
            new_v = convert_string(e.text())
        return new_v      
    
    """ Public interface """
    def has_options_widget(self):
        """Called from settings dialog. Override if you have a custom options widget."""
        return self.has_options() and self.is_activated
    
    def create_options_widget(self, parent):
        """Called from settings dialog. Override to create custom widgets."""
        from PyQt4.QtGui import QWidget, QGridLayout
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
    
    def update_options_widget(self):
        """Called every time an options widget is displayed"""
        if self.options is None:
            return
        for o in self.options:
            choiceOptions = self._getChoiceOptions(o)
            if choiceOptions is not None and choiceOptions != self.option_choice[o]:
                combo = self.option_widgets[o]
                self._initChoiceOption(o, combo, choiceOptions, self.get_option(o))
                
    def destroy_options_widget(self):
        """Called before the options widget is removed from its parent."""
        pass
    
    def extendsInfoDict(self):
        """Returns True if this plugin overrides extendInfoDict"""
        return False
    
    def extendInfoDict(self, infoDict):
        """Plugins can use this method to modify the info dict
        
        Make sure that extendsInfoDict() returns True.
        """
        pass
    
    def get_peer_actions(self):
        """Returns a list of PeerAction instances"""
        return None
    
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
        return self.plugin_name
    
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
    
    """ DB functions """ 
        
    def add_supported_dbms(self, db_type, db_iface):
        """
        calling this method allows DB connections of type db_type (can also be "default")
        when called at least once, the class db_iface will be initialized every time the 
        db connection is changed
        """
        if not issubclass(db_iface, db_for_plugin_iface):
            raise Exception("Adding supported DBMS only allowed via class inherited for db_for_plugin_iface")
        self._supported_dbms[db_type] = db_iface
        
    def get_supported_connections(self):
        from lunchinator import get_settings
        if not self._supported_dbms or u"default" in self._supported_dbms:
            return get_settings().get_available_db_connections()
         
        conns = []
        for connName in get_settings().get_available_db_connections():
            connType = get_connection_type(self.logger, connName)
            if connType in self._supported_dbms:
                conns.append(connName)
        return conns
        
    @loggingFunc
    def connect_to_db(self, changedDBConn=None):
        """
        connects to a database or changes the database connection type.
        """
        with self._specialized_db_connect_lock:
            if self._specialized_db_conn and changedDBConn and changedDBConn == self.options["db_connection"]:
                return
            if changedDBConn is None:
                changedDBConn = self.options[u"db_connection"]
            dbPlugin, plugin_type = get_db_connection(self.logger, changedDBConn)
            
            if dbPlugin == None:
                self.logger.warning("Plugin %s: DB  connection %s not available: Maybe DB Connections are not active yet?", type(self), self.options["db_connection"])
                return False
            
            if plugin_type in self._supported_dbms:
                self._specialized_db_conn = self._supported_dbms[plugin_type](dbPlugin, self.logger)
            elif "default" in self._supported_dbms:
                self._specialized_db_conn = self._supported_dbms["default"](dbPlugin, self.logger)
            else:
                self.logger.error("DB Conn of type %s is not supported by this plugin", plugin_type)
                self._specialized_db_conn = None
                return False
                
            self.logger.debug("Plugin %s uses DB Connection of type %s ", type(self), plugin_type)
                        
            return True
            
    def reconnect_db(self, _, newConnection):
        """method for changed options callback"""
        self.connect_to_db(newConnection)
        
    def is_db_ready(self):
        return self._specialized_db_conn and self._specialized_db_conn.is_open()
    
    def specialized_db_conn(self):
        return self._specialized_db_conn
    
    """ Used for testing """
    
    @classmethod
    def prepare_application(cls, beforeCreate, factory):
        from PyQt4.QtGui import QApplication, QMainWindow
        from lunchinator import get_settings
        from lunchinator.log import initializeLogger
        from lunchinator.log.lunch_logger import setGlobalLoggingLevel
        from lunchinator.utilities import setValidQtParent
    
        initializeLogger()
        get_settings().set_verbose(True)
        setGlobalLoggingLevel(logging.DEBUG)    
        app = QApplication(sys.argv)
        
        beforeCreate()
        
        window = QMainWindow()
        
        setValidQtParent(window)
        window.setWindowTitle("Layout Example")
        window.resize(300, 300)
        window.setCentralWidget(factory(window))
        window.showNormal()
        window.raise_()
        window.activateWindow()
        return window, app
    
    def _init_run_options_widget(self, parent):
        return self.create_options_widget(parent)
    
    def run_options_widget(self):
        self.setPluginName(u"Settings Test")
        self.hasConfigOption = lambda _ : False
        _window, app = iface_general_plugin.prepare_application(self.activate, self._init_run_options_widget)
        return app.exec_()
                    
class db_for_plugin_iface(object):
    """to support different DBMS within a plugin, a class inherited from this one is needed"""
    
    def __init__(self, newconn, logger):
        self.dbConn = newconn
        self.logger = logger
        
        try:
            self.init_db()
        except:
            self.logger.exception("Problem while migrating dataset to new version")
    
    def is_open(self):
        if self.dbConn != None:
            return self.dbConn.isOpen()
        return False
    
    def get_db_conn(self):
        return self.dbConn
    
    def init_db(self):
        """
        This method must be overwritten to create necessary tables
        it is also possible to migrate tables from older versions
        """
        raise NotImplementedError("Initialization not implemented")
        
class iface_general_plugin(iface_plugin): 
    pass

class iface_called_plugin(iface_plugin):
    def processes_events_immediately(self):
        """Override if the plugin can process events without peer information.
        
        If this method returns True, process_message, process_lunch_call
        and process_event may be called even though the sending peer is
        not known yet. Note that member_info will be None if the peer
        is unknown.
        """ 
        return False
    
    def processes_all_peer_actions(self):
        """Override if plugin processes all (non-blocked) peer actions.""" 
        return False
        
    def process_command(self, xmsg, ip, member_info, preprocessedData=None):
        """process extended Messages - can be signed
        @type xmsg: extMessageIncoming
        @type ip: unicode
        @type member_info: dict   
        """
        pass
    
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        """process extended Messages - can be signed
        @type xmsg: extMessageIncoming
        @type ip: unicode
        @type member_info: dict   
        @type lunch_call: bool
        """
        pass
    
    """ deprecated interface that is still supported: """        
    def process_message(self, msg, ip, member_info):
        pass
        
    def process_lunch_call(self, msg, ip, member_info):
        pass
        
    def process_event(self, cmd, value, ip, member_info, preprocessedData=None):
        pass 
        
class iface_gui_plugin(iface_plugin):
    def __init__(self):
        super(iface_gui_plugin, self).__init__()
        self.sortOrder = -1
        
    def create_widget(self, _parent):
        return None
    
    def destroy_widget(self):
        """Called when the widget is hidden / closed. Ensure that create_widget restores the state."""
        pass
    
    def create_menus(self, _menuBar):
        """Creates plugin specific menus and returns a list of QMenu objects"""
        return None
    
    @classmethod
    def run_standalone(cls, factory):
        _window, app = cls.prepare_application(lambda : None, factory)
        sys.exit(app.exec_())
        
    def run_in_window(self, callAfterCreate=None):
        self.setPluginName(u"GUI Test")
        _window, app = iface_gui_plugin.prepare_application(self.activate, lambda window : self.create_widget(window))
        if callAfterCreate:
            callAfterCreate()
        sys.exit(app.exec_())
        
    def processes_events_immediately(self):
        """Override if the plugin can process events without peer information.
        
        If this method returns True, process_message, process_lunch_call
        and process_event may be called even though the sending peer is
        not known yet. Note that member_info will be None if the peer
        is unknown.
        """ 
        return False
    
    def processes_all_peer_actions(self):
        """Override if plugin processes all (non-blocked) peer actions.""" 
        return False
        
    def process_command(self, xmsg, ip, peer_info, preprocessedData=None):
        """process extended Messages - can be signed
        @type xmsg: extMessageIncoming
        @type ip: unicode
        @type member_info: dict   
        """
        pass    
    
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        """process extended Messages - can be signed
        @type xmsg: extMessageIncoming
        @type ip: unicode
        @type member_info: dict   
        @type lunch_call: bool
        """
        pass
    
    """ deprecated interface that is still supported: """    
    def process_message(self, msg, ip, member_info):
        pass
        
    def process_lunch_call(self, msg, ip, member_info):
        pass
        
    def process_event(self, cmd, value, ip, member_info, preprocessedData=None):
        pass
