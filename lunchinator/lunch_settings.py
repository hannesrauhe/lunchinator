import sys, os, getpass, ConfigParser, types, logging, codecs, contextlib, uuid

'''integrate the cli-parser into the default_config sooner or later'''
from lunchinator import log_exception, log_error, setLoggingLevel, convert_string, MAIN_CONFIG_DIR,\
    log_warning, get_notification_center
from datetime import datetime
import json
from lunchinator.repositories import PluginRepositories
import inspect

_GENERAL_SETTINGS = []
_HIDDEN_SETTINGS = set()

def setting(gui=False, desc=None, sendInfoDict=False, restart=False, choice=None):
    def setting_wrap(func):
        prefix = func.__name__[:3]
        option = func.__name__[4:]
        
        if gui:
            if type(choice) not in (tuple, list):
                _GENERAL_SETTINGS.append(((option, desc), None))
            else:
                _GENERAL_SETTINGS.append(((option, desc, choice), None))
        else:
            _HIDDEN_SETTINGS.add(option)
        
        if prefix == "set":
            def newFunc(self, *args, **kwargs):
                isInit = False
                if "init" in kwargs:
                    isInit = kwargs["init"]
                    argspec, _varargs, _varkw, _defaults = inspect.getargspec(func)
                    if not "init" in argspec:
                        del kwargs["init"]
                    
                if isInit:
                    sendInfo = False
                else:
                    sendInfo = sendInfoDict
                    if "sendInfoDict" in kwargs:
                        sendInfo = kwargs["sendInfoDict"]
                        del kwargs["sendInfoDict"]
                
                attrname = "_" + option
                if hasattr(self, attrname): 
                    old_v = getattr(self, attrname)
                    new_v = args[0]
                    if type(old_v) != type(new_v):
                        log_error("Value of setting", option, "has wrong type.")
                        return
                else:
                    log_warning("settings has attribute '%s'" % attrname)

                func(self, *args, **kwargs)
    
                if hasattr(self, attrname): 
                    new_v = getattr(self, attrname)
                    
                    if not isInit:
                        # override category as "general"
                        self.get_config_file().set('general', option, unicode(new_v))
                    
                if gui and not isInit:
                    get_notification_center().emitGeneralSettingChanged(option)
                
                if sendInfo:
                    from lunchinator import get_server
                    get_server().call_info()
                if not isInit and restart:
                    get_notification_center().emitRestartRequired("Some changed settings require a restart")
            return newFunc
        return func
    return setting_wrap

def gui_setting(desc, sendInfoDict=False, restart=False, choice=None):
    """Decorator for GUI settings
    
    sendInfoDict -- True to send info dictionary on changes
    restart -- True to send restart notification on changes
    choice -- List or tuple of strings as a choice of options
    """
    return setting(gui=True, desc=desc, sendInfoDict=sendInfoDict, restart=restart, choice=choice)

def hidden_setting(sendInfoDict=False):
    """Decorator for hidden settings
    
    sendInfoDict -- True to send info dictionary on changes
    """
    return setting(gui=False, sendInfoDict=sendInfoDict)

class lunch_settings(object):
    LUNCH_TIME_FORMAT = "%H:%M"
    LUNCH_TIME_FORMAT_QT = "HH:mm"
    _instance = None
    
    @classmethod
    def get_singleton_instance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
        
    @classmethod
    def get_gui_settings(cls):
        return _GENERAL_SETTINGS
    
    @classmethod
    def get_hidden_settings(cls):
        return _HIDDEN_SETTINGS
    
    def __init__(self):
        self._main_config_dir = MAIN_CONFIG_DIR
        self._members_file = self.get_config("lunch_members.cfg") # DEPRECATED, use peers_file
        self._peers_file = self.get_config("lunch_peers.cfg")
        self._legacy_messages_file = self.get_config("messages")
        self._messages_file = self.get_config("messages.sqlite")
        self._log_file = self.get_config("lunchinator.log")
        self._avatar_dir = self.get_config("avatars")
        self._version = None
        self._commit_count = None
        self._commit_count_plugins = "-1"
        self._main_package_path = self._findMainPackagePath()
        if self._main_package_path == None:
            raise Exception("Could not determine path to the main lunchinator package.")
        self._resources_path = self._findResourcesPath(self._main_package_path)
        if self._resources_path == None:
            raise Exception("Could not determine path to the lunchinator resource files.")
        self._load_plugins = True
        self._plugin_repos = None
        
        # configurable  
        self._lunch_trigger = u"lunch"
        self._user_name = getpass.getuser().decode() 
        self._group = u""
        self._avatar_file = u""    
        self._tcp_port = 50001
        self._default_lunch_begin = u"12:15"
        self._default_lunch_end = u"12:45"
        self._alarm_begin_time = u"11:30"
        self._alarm_end_time = u"13:00"
        self._mute_timeout = 30
        self._verbose = False
        self._logging_level = u"ERROR"
        self._group_plugins = False
        self._default_db_connection = u"Standard"
        self._available_db_connections = u"Standard"  # list separated by ;; (like yapsy)
        self._proxy = u""
        self._warn_if_members_not_ready = True
                
        #also in config, but hidden
        self._ID = u""
        self._peer_timeout = 300
        
        self._next_lunch_begin = None
        self._next_lunch_end = None
        
        if not os.path.exists(self._main_config_dir):
            os.makedirs(self._main_config_dir)
        if not os.path.exists(self._avatar_dir):
            os.makedirs(self._avatar_dir)
            
        self._config_file = ConfigParser.SafeConfigParser()
        self.read_config_from_hd()
        
        # insert plugin folders into path
        for aDir in self.get_plugin_dirs():
            # TODO check first!
            sys.path.insert(0, aDir)
            
    def _findMainPackagePath(self):
        path = os.path.realpath(__file__) 
        while os.path.dirname(path) != path:
            if os.path.exists(os.path.join(path, 'lunchinator', '__init__.py')):
                return path
            path = os.path.dirname(path)
        if hasattr(sys, "_MEIPASS"):  #pyinstaller, only for Windows
            return sys._MEIPASS
        return None
    
    def _findResourcesPath(self, defaultPath):    
        possibilities = [defaultPath, "/usr/share/lunchinator", "/usr/local/share/lunchinator"]
        if hasattr(sys, "_MEIPASS"): #pyinstaller            
            possibilities = [os.path.dirname(sys.executable)] + possibilities
        for poss in possibilities:
            if os.path.exists(os.path.join(poss, "images", "lunchinator.png")):
                return poss
        return None    
    
    def get_plugins_enabled(self):
        return self._load_plugins
    
    def set_plugins_enabled(self, enable):
        self._load_plugins = enable
            
    def set_option(self, o, v, **kwargs):
        """Set an option by its name.
        
        o -- option name
        v -- new value
        init -- True when the option is set to its initial value.
        """
        methodname = "set_" + o
        if hasattr(self, methodname): 
            _member = getattr(self, methodname)
            _member(v, **kwargs)
        else:
            log_warning("settings has no setter for '%s'" % o)
        
        return self.get_option(o)
    
    def get_option(self, o):
        """Get an option by its name."""
        methodname = "get_" + o
        if hasattr(self, methodname): 
            _member = getattr(self, methodname)
            return _member()
        else:
            log_warning("settings has no attribute called '%s'" % o)
        return None
            
    def read_config_from_hd(self): 
        self._config_file.read(self._main_config_dir + '/settings.cfg')
        
        # load gui settings
        for tup, _val in self.get_gui_settings():
            option = tup[0]
            value = self.read_value_from_config_file(self.get_option(option), "general", option)
            self.set_option(option, value, init=True)
            
        # load hidden settings
        for option in self.get_hidden_settings():
            value = self.read_value_from_config_file(self.get_option(option), "general", option)
            self.set_option(option, value, init=True)
        
        # load settings that don't fit the default schema        
        self._ID = self.read_value_from_config_file(self._ID, "general", "ID")      
        self._available_db_connections = self.read_value_from_config_file(self._available_db_connections, "general", "available_db_connections")
        externalRepos = self.read_value_from_config_file(None, "general", "external_plugin_repos")
        if externalRepos == None:
            if os.path.isdir(self.get_config("plugins")):
                externalRepos = [(self.get_config("plugins"), True, False)]  # active, but no auto update
            else:
                externalRepos = []
        else:
            externalRepos = json.loads(externalRepos)
            
        self._plugin_repos = PluginRepositories(self.get_resource("plugins"), externalRepos, logging=self.get_verbose())
        
        if len(self._ID)==0:
            self._ID = unicode(uuid.uuid4())
            self._config_file.set('general', 'ID', self._ID )
        
            
    def read_value_from_config_file(self, value, section, name):
        try:
            if type(value) is types.BooleanType:
                value = self._config_file.getboolean(section, name)
            elif type(value) is types.IntType:
                value = self._config_file.getint(section, name)
            else:
                value = unicode(self._config_file.get(section, name))
        except ConfigParser.NoSectionError:
            self._config_file.add_section(section)
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            log_error("Value of setting", name, "has wrong type.")
        except:
            log_exception("error while reading %s from config file", name)
        return value
        
    def write_config_to_hd(self):
        self.get_config_file().set('general', 'external_plugin_repos', json.dumps(self.get_plugin_repositories().getExternalRepositories()))
        with codecs.open(self._main_config_dir + '/settings.cfg', 'w', 'utf-8') as f: 
            self._config_file.write(f)
    
    def get_main_package_path(self):
        return self._main_package_path
    
    def get_resources_path(self):
        return self._resources_path
    
    def get_resource(self, *args):
        res = unicode(os.path.join(self.get_resources_path(), *args))
        if not os.path.exists(res):
            raise Exception("Resource %s does not exist." % res)
        return res
    
    def get_main_config_dir(self):
        return self._main_config_dir
    
    def get_config(self, *args):
        return unicode(os.path.join(self.get_main_config_dir(), *args))
    
    def get_plugin_dirs(self):
        # getPluginDirs is thread safe
        return self._plugin_repos.getPluginDirs()
    
    def get_plugin_repositories(self):
        return self._plugin_repos

    def get_config_file(self):
        return self._config_file
    
    def get_peers_file(self):
        return self._peers_file
    
    def get_members_file(self):
        """Deprecated: Use get_peers_file"""
        return self._members_file
    
    def get_messages_file(self):
        return self._messages_file

    def get_legacy_messages_file(self):
        return self._legacy_messages_file
    
    def get_version(self):
        if not self._version:
            try:
                version_file = self.get_resource("version")
                with contextlib.closing(open(version_file, "r")) as vfh:
                    self._version = vfh.read().strip()
                self._commit_count = self._version.split(".")[-1]
            except Exception:
                from lunchinator.git import GitHandler
                if GitHandler.hasGit():
                    commit_count = GitHandler.getCommitCount()
                    if commit_count:
                        self._commit_count = commit_count
                        self._version = commit_count
                else:
                    log_error("Error reading/parsing version file")
                    self._version = u"unknown.unknown"
                    self._commit_count = "unknown"
                
        return self._version
    
    def get_commit_count(self):
        self.get_version()
        
        return self._commit_count
    
    def get_commit_count_plugins(self):
        return self._commit_count_plugins
    
    def get_log_file(self):
        return self._log_file
    
    def get_ID(self):
        return self._ID
    
    # the rest is read from/written to the config file
    def get_user_name(self):
        return self._user_name    
    @gui_setting(u"User Name", sendInfoDict=True)
    def set_user_name(self, name):
        self._user_name = convert_string(name)
       
    def get_lunch_trigger(self):
        return self._lunch_trigger
    @gui_setting(u"Word that triggers alarm")
    def set_lunch_trigger(self, value):
        self._lunch_trigger = value
             
    def get_group(self):
        return self._group
    @gui_setting(u"Group Name")
    def set_group(self, value, init=False):
        from lunchinator import get_server
        self._group = value
        if not init:
            get_server().changeGroup(unicode(value))
      
    def get_avatar_dir(self):
        return self._avatar_dir
                 
    def get_avatar_file(self):
        return self.get_avatar()
    @hidden_setting()
    def set_avatar_file(self, file_name):  
        if file_name and not os.path.exists(os.path.join(self._avatar_dir, file_name)):
            log_error("avatar does not exist: %s", file_name)
            return
        self._avatar_file = convert_string(file_name)
        
    def get_avatar(self):
        return self._avatar_file
    
    def _check_lunch_time(self, new_value, old_value):
        if new_value == old_value:
            return new_value
        try:
            time = datetime.strptime(new_value, lunch_settings.LUNCH_TIME_FORMAT)
            if time:
                return new_value
        except:
            log_error("Problem while checking the lunch time")
        log_error("Illegal time format:", new_value)
        return old_value
    
    def get_default_lunch_begin(self):
        return self._default_lunch_begin
    @gui_setting(u"Free for lunch from", sendInfoDict=True)
    def set_default_lunch_begin(self, new_value):
        new_value = convert_string(new_value)
        self._default_lunch_begin = self._check_lunch_time(new_value, self._default_lunch_begin)
    
    def get_default_lunch_end(self):
        return self._default_lunch_end
    @gui_setting(u"Free for lunch until", sendInfoDict=True)
    def set_default_lunch_end(self, new_value):
        new_value = convert_string(new_value)
        self._default_lunch_end = self._check_lunch_time(new_value, self._default_lunch_end)
        
    def get_next_lunch_begin(self):
        # reset "next" lunch times after they are over
        if self._next_lunch_begin:
            return self._next_lunch_begin
        return self.get_default_lunch_begin()
        
    def get_next_lunch_end(self):
        # reset "next" lunch times after they are over
        if self._next_lunch_end:
            if self.get_next_lunch_reset_time() > 0:
                return self._next_lunch_end
            else:
                # reset
                self._next_lunch_begin = None
                self._next_lunch_end = None
        return self.get_default_lunch_end()
    
    def set_next_lunch_time(self, begin_time, end_time):
        if begin_time == None:
            self._next_lunch_begin, self._next_lunch_end = None, None
            
        begin_time = convert_string(begin_time)
        self._next_lunch_begin = self._check_lunch_time(begin_time, self._next_lunch_begin)
        end_time = convert_string(end_time)
        self._next_lunch_end = self._check_lunch_time(end_time, self._next_lunch_end)
    
    def get_next_lunch_reset_time(self):
        if self._next_lunch_end == None:
            return None
        
        from lunchinator.utilities import getTimeDelta
        # reset after next_lunch_end, but not before default_lunch_end
        
        tdn = getTimeDelta(self._next_lunch_end)
        tdd = getTimeDelta(self.get_default_lunch_end())
        
        return max(tdn, tdd)
    def get_warn_if_members_not_ready(self):
        return self._warn_if_members_not_ready
    @gui_setting(u"Warn if members are not ready for lunch")
    def set_warn_if_members_not_ready(self, new_value):
        self._warn_if_members_not_ready = new_value
    
    def get_alarm_begin_time(self):
        return self._alarm_begin_time
    @gui_setting(u"No alarm before")
    def set_alarm_begin_time(self, new_value):
        new_value = convert_string(new_value)
        self._alarm_begin_time = self._check_lunch_time(new_value, self._alarm_begin_time)
    
    def get_alarm_end_time(self):
        return self._alarm_end_time
    @gui_setting(u"No alarm after")
    def set_alarm_end_time(self, new_value):
        new_value = convert_string(new_value)
        self._alarm_end_time = self._check_lunch_time(new_value, self._alarm_end_time)
    
    def get_mute_timeout(self):
        return self._mute_timeout
    @gui_setting(u"Mute for x sec after alarm")
    def set_mute_timeout(self, new_value):
        self._mute_timeout = new_value
    
    def get_peer_timeout(self):
        return self._peer_timeout
    @hidden_setting()
    def set_peer_timeout(self, v):
        self._peer_timeout = v
        
    def get_tcp_port(self):
        return self._tcp_port
    @gui_setting(u"TCP port", restart=True)
    def set_tcp_port(self, new_value):
        self._tcp_port = new_value
    
    def get_logging_level(self):
        return self._logging_level
    @gui_setting(u"Logging level", choice=(u"CRITICAL", u"ERROR", u"WARNING", u"INFO", u"DEBUG"))
    def set_logging_level(self, newValue):
        self._logging_level = convert_string(newValue)
        if self._logging_level == u"CRITICAL":
            setLoggingLevel(logging.CRITICAL)
        elif self._logging_level == u"ERROR":
            setLoggingLevel(logging.ERROR)
        elif self._logging_level == u"WARNING":
            setLoggingLevel(logging.WARNING)
        elif self._logging_level == u"INFO":
            setLoggingLevel(logging.INFO)
        elif self._logging_level == u"DEBUG":
            setLoggingLevel(logging.DEBUG)
        
    def set_verbose(self, verbose):
        """Set True to override logging level"""
        self._verbose = verbose
    def get_verbose(self):
        return self._verbose or self._logging_level == u"DEBUG"
        
    def get_group_plugins(self):
        return self._group_plugins
    @gui_setting(u"Group plugins by category", restart=True)
    def set_group_plugins(self, newValue):
        self._group_plugins = newValue            
        
    def get_default_db_connection(self):
        return self._default_db_connection
    
    def set_default_db_connection(self, newValue):
        self._default_db_connection = newValue
        
    # always force at least one connection
    def get_available_db_connections(self):
        conn = [unicode(x) for x in self._available_db_connections.split(";;")]
        if len(conn):
            return conn
        else:
            return [u'Standard']
    
    def set_available_db_connections(self, newValue):
        self._available_db_connections = ";;".join(newValue)
        self._config_file.set('general', 'available_db_connections', str(self._available_db_connections))
            
    def get_advanced_gui_enabled(self):
        return self._logging_level == u"DEBUG"
        
    def get_proxy(self):
        return self._proxy
    @gui_setting(u"Proxy server (usually detected automatically)", restart=True)
    def set_proxy(self, newValue, init=False):
        if newValue:
            os.environ["http_proxy"] = newValue
            os.environ["https_proxy"] = newValue
        elif not init:
            if "http_proxy" in os.environ:
                del os.environ["http_proxy"]
            if "https_proxy" in os.environ:
                del os.environ["https_proxy"]
        self._proxy = newValue
        
