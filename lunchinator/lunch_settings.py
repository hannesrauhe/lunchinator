import sys, os, getpass, ConfigParser, types, logging, codecs, contextlib, uuid

'''integrate the cli-parser into the default_config sooner or later'''
from lunchinator import log_exception, log_error, setLoggingLevel, convert_string, MAIN_CONFIG_DIR
from datetime import datetime
import json
from lunchinator.repositories import PluginRepositories

class lunch_settings(object):
    LUNCH_TIME_FORMAT = "%H:%M"
    LUNCH_TIME_FORMAT_QT = "HH:mm"
    _instance = None
    
    @classmethod
    def get_singleton_instance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
        
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

    def __init__(self):
        '''unchangeable for now'''
        self._main_config_dir = MAIN_CONFIG_DIR
        self._members_file = self.get_config("lunch_members.cfg") # DEPRECATED, use peers_file
        self._peers_file = self.get_config("lunch_peers.cfg")
        self._messages_file = self.get_config("messages")
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
        
        self._plugin_repos = None
        
        # configurable  
        self._lunch_trigger = u"lunch"
        self._user_name = u""
        self._group = u""
        self._avatar_file = u""    
        self._tcp_port = 50001
        self._default_lunch_begin = u"12:15"
        self._default_lunch_end = u"12:45"
        self._alarm_begin_time = u"11:30"
        self._alarm_end_time = u"13:00"
        self._mute_timeout = 30
        self._reset_icon_time = 5
        self._logging_level = u"ERROR"
        self._group_plugins = False
        self._default_db_connection = u"Standard"
        self._available_db_connections = u"Standard"  # list separated by ;; (like yapsy)
        self._proxy = u""
        self._warn_if_members_not_ready = True
                
        #also in config, but hidden
        self._ID = u""
        self._member_timeout = 300
        self._peer_timeout = 10000
        
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
            
    def read_config_from_hd(self): 
        self._config_file.read(self._main_config_dir + '/settings.cfg')
        
        self._user_name = self.read_value_from_config_file(self._user_name, "general", "user_name")
        self._group = self.read_value_from_config_file(self._group, "general", "group")
        self._tcp_port = self.read_value_from_config_file(self._tcp_port, "general", "tcp_port")
        
        self.set_default_lunch_begin(self.read_value_from_config_file(self._default_lunch_begin, "general", "default_lunch_begin"))
        self.set_default_lunch_end(self.read_value_from_config_file(self._default_lunch_end, "general", "default_lunch_end"))
        self.set_alarm_begin_time(self.read_value_from_config_file(self._alarm_begin_time, "general", "alarm_begin_time"))
        self.set_alarm_end_time(self.read_value_from_config_file(self._alarm_end_time, "general", "alarm_end_time"))
        
        self._mute_timeout = self.read_value_from_config_file(self._mute_timeout, "general", "mute_timeout")
        self._reset_icon_time = self.read_value_from_config_file(self._reset_icon_time, "general", "reset_icon_time")
        
        self._logging_level = self.read_value_from_config_file(self._logging_level, 'general', 'logging_level')
        self._group_plugins = self.read_value_from_config_file(self._group_plugins, 'general', 'group_plugins')
        self._lunch_trigger = self.read_value_from_config_file(self._lunch_trigger, 'general', 'lunch_trigger')
        
        # not shown in settings-plugin
        self._avatar_file = self.read_value_from_config_file(self._avatar_file, "general", "avatar_file")
        self._available_db_connections = self.read_value_from_config_file(self._available_db_connections, "general", "available_db_connections")
        self._ID = self.read_value_from_config_file(self._ID, "general", "ID")      
        self._member_timeout = self.read_value_from_config_file(self._member_timeout, "general", "member_timeout")   
        self._peer_timeout = self.read_value_from_config_file(self._peer_timeout, "general", "peer_timeout")    
   
        
        externalRepos = self.read_value_from_config_file(None, "general", "external_plugin_repos")
        if externalRepos == None:
            if os.path.isdir(self.get_config("plugins")):
                externalRepos = [(self.get_config("plugins"), True, False)]  # active, but no auto update
            else:
                externalRepos = []
        else:
            externalRepos = json.loads(externalRepos)
            
        self._plugin_repos = PluginRepositories(self.get_resource("plugins"), externalRepos, logging=self.get_logging_level() == logging.DEBUG)
        
        if self._user_name == "":
            self._user_name = getpass.getuser().decode()         
        
        if len(self._ID)==0:
            self._ID = unicode(uuid.uuid4())
            self._config_file.set('general', 'ID', self._ID )
        
        # apply proxy on start if given
        self._proxy = self.read_value_from_config_file(self._proxy, "general", "proxy")  
        if self._proxy:
            self.set_proxy(self._proxy)
            
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
    def get_lunch_trigger(self):
        return self._lunch_trigger
    def set_lunch_trigger(self, value):
        self._lunch_trigger = value
             
    def get_user_name(self):
        return self._user_name    
    def set_user_name(self, name):
        self._user_name = convert_string(name)
        self._config_file.set('general', 'user_name', self._user_name)
       
    def get_group(self):
        return self._group
    def set_group(self, value):
        self._group = value
      
    def get_avatar_dir(self):
        return self._avatar_dir
                 
    def get_avatar_file(self):
        return self.get_avatar()
    def set_avatar_file(self, file_name, _something):  
        if not os.path.exists(self._avatar_dir + "/" + file_name):
            log_error("avatar does not exist: %s", file_name)
            return
        self._avatar_file = convert_string(file_name)
        self._config_file.set('general', 'avatar_file', str(file_name))
        
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
    def set_default_lunch_begin(self, new_value):
        new_value = convert_string(new_value)
        self._default_lunch_begin = self._check_lunch_time(new_value, self._default_lunch_begin)
    
    def get_default_lunch_end(self):
        return self._default_lunch_end
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
    def set_warn_if_members_not_ready(self, new_value):
        self._warn_if_members_not_ready = new_value
    
    def get_alarm_begin_time(self):
        return self._alarm_begin_time
    def set_alarm_begin_time(self, new_value):
        new_value = convert_string(new_value)
        self._alarm_begin_time = self._check_lunch_time(new_value, self._alarm_begin_time)
    
    def get_alarm_end_time(self):
        return self._alarm_end_time
    def set_alarm_end_time(self, new_value):
        new_value = convert_string(new_value)
        self._alarm_end_time = self._check_lunch_time(new_value, self._alarm_end_time)
    
    def get_mute_timeout(self):
        return self._mute_timeout
    def set_mute_timeout(self, new_value):
        self._mute_timeout = new_value
    
    def get_peer_timeout(self):
        return self._peer_timeout
    def get_member_timeout(self):
        return self._member_timeout
    
    def get_tcp_port(self):
        return self._tcp_port
    def set_tcp_port(self, new_value):
        self._tcp_port = new_value
    
    def get_reset_icon_time(self):
        return self._reset_icon_time
    def set_reset_icon_time(self, new_value):
        self._reset_icon_time = new_value
    
    def get_logging_level(self):
        return self._logging_level
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
        
    def get_group_plugins(self):
        return self._group_plugins
    
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
    
    def set_proxy(self, newValue):
        os.environ["http_proxy"] = newValue
        os.environ["https_proxy"] = newValue
        self._proxy = newValue
        
