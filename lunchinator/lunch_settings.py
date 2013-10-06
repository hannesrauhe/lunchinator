import sys,os,getpass,ConfigParser,types,subprocess,logging,codecs

'''integrate the cli-parser into the default_config sooner or later'''
from lunchinator import log_exception, log_warning, log_error, setLoggingLevel, convert_string
    
class lunch_settings(object):
    _instance = None
    
    @classmethod
    def get_singleton_instance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
    
    def runGitCommand(self, args, path = None, quiet = True):
        if path == None:
            path = self._lunchdir
        
        call = ["git","--git-dir="+path+"/.git","--work-tree="+path]
        call = call + args
        
        fh = subprocess.PIPE    
        if quiet:
            fh = open(os.path.devnull,"w")
        p = subprocess.Popen(call,stdout=fh, stderr=fh)
        pOut, pErr = p.communicate()
        retCode = p.returncode
        return retCode, pOut, pErr
    
    def getGitCommandResult(self, args, path = None, quiet = True):
        retCode, _, __ = self.runGitCommand(args, path, quiet)
        return retCode
    
    def __init__(self):
        '''unchangeable for now'''
        self._main_config_dir = unicode(os.getenv("HOME")+os.path.sep+".lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+os.path.sep+".lunchinator")
        self._members_file = unicode(self._main_config_dir+os.path.sep+"lunch_members.cfg")
        self._messages_file = unicode(self._main_config_dir+os.path.sep+"messages")
        self._log_file = unicode(self._main_config_dir+os.path.sep+"lunchinator.log")
        self._avatar_dir = unicode(self._main_config_dir+os.path.sep+"avatars"+os.path.sep)
        self._version = u"unknown"
        self._version_short = u"unknown"
        self._commit_count = "0"
        self._commit_count_plugins = "-1"
        self._lunchdir = sys.path[0]
        self._internal_plugin_dir = unicode(self._lunchdir+os.path.sep+"plugins"+os.path.sep)
        self._external_plugin_dir = unicode(self._main_config_dir+os.path.sep+"plugins")
        self._plugin_dirs = [self._internal_plugin_dir, self._external_plugin_dir]
        
        #insert plugin folders into path
        for aDir in self._plugin_dirs:
            sys.path.insert(0, aDir)
        
        ''' not in files'''    
        self._next_lunch_begin = None
        self._next_lunch_end = None
        self._audio_file = unicode(self._lunchdir+os.path.sep+"sounds"+os.path.sep+"sonar.wav")
        self._user_name = u""
        self._avatar_file = u""    
        self._tcp_port = 50001
        self._auto_update = True   
        self._default_lunch_begin = u"12:15"
        self._default_lunch_end = u"12:45"
        self._alarm_begin_time = u"11:30"
        self._alarm_end_time = u"13:00"
        self._peer_timeout = 604800 #one week so that we don't forget someone too soon
        self._mute_timeout = 30
        self._reset_icon_time = 5
        self._logging_level = u"ERROR"
        
        if not os.path.exists(self._main_config_dir):
            os.makedirs(self._main_config_dir)
        if not os.path.exists(self._avatar_dir):
            os.makedirs(self._avatar_dir)
        
        try:
            _, self._version, __ = self.runGitCommand(["log", "-1"], self._lunchdir, quiet=False)
            for line in self._version.splitlines():
                if line.startswith("Date:"):
                    self._version_short = unicode(line[5:].strip())            
        except:
            log_exception("git log could not be executed correctly - version information not available")
        
        try:    
            revListArgs = ["rev-list", "HEAD", "--count"]
            _, cco, __ = self.runGitCommand(revListArgs, self._lunchdir, quiet=False)
            self._commit_count = cco.strip()
            
            if os.path.exists(self._external_plugin_dir):
                retCode, cco, __ = self.runGitCommand(revListArgs, self._external_plugin_dir, quiet=False)
                if retCode == 0:
                    self._commit_count_plugins = cco.strip()
        except:
            log_exception("git rev-list could not be executed correctly - commit count information not available")
            
        self._config_file = ConfigParser.SafeConfigParser()
        self.read_config_from_hd()
            
    def read_config_from_hd(self): 
        self._config_file.read(self._main_config_dir+'/settings.cfg')
        
        self._user_name = self.read_value_from_config_file(self._user_name,"general","user_name")
        self._tcp_port = self.read_value_from_config_file(self._tcp_port,"general","tcp_port")
        
        self._auto_update = self.read_value_from_config_file(self._auto_update,"general","auto_update")
        self._default_lunch_begin = self.read_value_from_config_file(self._default_lunch_begin,"general","default_lunch_begin")
        self._default_lunch_end = self.read_value_from_config_file(self._default_lunch_end,"general","default_lunch_end")
        self._alarm_begin_time = self.read_value_from_config_file(self._alarm_begin_time,"general","alarm_begin_time")
        self._alarm_end_time = self.read_value_from_config_file(self._alarm_end_time,"general","alarm_end_time")
        
        self._peer_timeout = self.read_value_from_config_file(self._peer_timeout, "general", "peer_timeout")
        self._mute_timeout = self.read_value_from_config_file(self._mute_timeout, "general", "mute_timeout")
        self._reset_icon_time = self.read_value_from_config_file(self._reset_icon_time, "general", "reset_icon_time")
        
        self._logging_level = self.read_value_from_config_file(self._logging_level, 'general', 'logging_level')
        
        #not shown in settings-plugin - handled by avatar-plugin
        self._avatar_file =  self.read_value_from_config_file(self._avatar_file,"general","avatar_file")
                     
        if os.path.exists(self._main_config_dir+"/username.cfg"):
            with codecs.open(self._main_config_dir+"/username.cfg",'r','utf-8') as f:
                self.set_user_name(f.readline().strip())
                
        if os.path.exists(self._main_config_dir+"/avatar.cfg"):
            with codecs.open(self._main_config_dir+"/avatar.cfg",'r','utf-8') as f:
                self.set_avatar_file(f.readline().strip())
                
        if os.path.exists(self._main_config_dir+"/sound.cfg"):
            with codecs.open(self._main_config_dir+"/sound.cfg",'r','utf-8') as f:
                audio_file = f.readline().strip()
                if os.path.exists(self._main_config_dir+"/sounds/"+audio_file):
                    self._audio_file = self._main_config_dir+"/sounds/"+audio_file
                elif os.path.exists(self._lunchdir+"/sounds/"+audio_file):
                    self._audio_file = self._lunchdir+"/sounds/"+audio_file
                else:
                    log_warning("configured audio file %s does not exist in sounds folder, using old one: %s",audio_file,self._audio_file)  
        
        if self._user_name=="":
            self._user_name = getpass.getuser()  
            
    def read_value_from_config_file(self,value,section,name):
        try:
            if type(value) is types.BooleanType:
                value = self._config_file.getboolean(section,name)
            elif type(value) is types.IntType:
                value = self._config_file.getint(section,name)
            else:
                value = unicode(self._config_file.get(section,name))
        except ConfigParser.NoSectionError:
            self._config_file.add_section(section)
        except ConfigParser.NoOptionError:
            pass
        except:
            log_exception("error while reading %s from config file",name)
        return value
        
    def write_config_to_hd(self):
        with codecs.open(self._main_config_dir+'/settings.cfg','w','utf-8') as f: 
            self._config_file.write(f)
        
    def getCanUpdate(self, repo):
        if self.getGitCommandResult(["rev-parse"], repo) != 0:
            return (False, "'%s' is no git repository" % repo)
        
        if self.getGitCommandResult(["diff","--name-only","--exit-code","--quiet"], repo) != 0:
            return (False, "There are unstaged changes")
        
        if self.getGitCommandResult(["diff","--cached","--exit-code","--quiet"], repo) != 0:
            return (False, "There are staged, uncommitted changes")
        
        _, branch, __ = self.runGitCommand(["symbolic-ref","HEAD"], repo, quiet=False)
        if "master" not in branch:
            return (False, "The selected branch is not the master branch")
        
        if self.getGitCommandResult("log","origin/master..HEAD","--exit-code","--quiet") != 0:
            return (False, "There are unpushed commits on the master branch")
        
        return (True, None)
    
    def getCanUpdateMain(self):
        return self.getCanUpdate(self._lunchdir)
        
    def getCanUpdatePlugins(self):
        return self.getCanUpdate(self._main_config_dir + "/plugins/")
    
    def get_auto_update_enabled(self):
        return self._auto_update
    def set_auto_update_enabled(self, enable):
        self._auto_update = enable
    
    def get_lunchdir(self):
        return self._lunchdir
    
    def get_main_config_dir(self):
        return self._main_config_dir
    
    def get_plugin_dirs(self):
        return self._plugin_dirs
    
    def get_config_file(self):
        return self._config_file
    
    def get_members_file(self):
        return self._members_file
    
    def get_messages_file(self):
        return self._messages_file
    
    def get_version_short(self):
        return self._version_short
    
    def get_commit_count(self):
        return self._commit_count
    
    def get_commit_count_plugins(self):
        return self._commit_count_plugins
    
    def get_next_lunch_begin(self):
        return self._next_lunch_begin
    
    def get_next_lunch_end(self):
        return self._next_lunch_end
    
    def get_log_file(self):
        return self._log_file
    
    #the rest is read from/written to the config file          
    def get_user_name(self):
        return self._user_name    
    def set_user_name(self,name,force_write=False):
        self._user_name = convert_string(name)
        self._config_file.set('general', 'user_name', self._user_name)
        if force_write:
            self.write_config_to_hd()
    
    def get_auto_update(self):
        return self._auto_update
    def set_auto_update(self, new_value):
        self._auto_update = new_value
    
    def get_audio_file(self):
        return self._audio_file 
    def set_audio_file(self, new_value):
        self._audio_file = convert_string(new_value)
      
    def get_avatar_dir(self):
        return self._avatar_dir
                 
    def get_avatar_file(self):
        return self.get_avatar()
    def set_avatar_file(self,file_name,force_write=False):  
        if not os.path.exists(self._avatar_dir+"/"+file_name):
            log_error("avatar does not exist: %s",file_name)
            return
        self._avatar_file = convert_string(file_name)
        self._config_file.set('general', 'avatar_file', str(file_name))
        if force_write:
            self.write_config_to_hd()
    
    def get_avatar(self):
        return self._avatar_file
    
    def get_default_lunch_begin(self):
        return self._default_lunch_begin
    def set_default_lunch_begin(self, new_value):
        self._default_lunch_begin = convert_string(new_value)
    
    def get_default_lunch_end(self):
        return self._default_lunch_end
    def set_default_lunch_end(self, new_value):
        self._default_lunch_end = convert_string(new_value)
    
    def get_alarm_begin_time(self):
        return self._alarm_begin_time
    def set_alarm_begin_time(self, new_value):
        self._alarm_begin_time = convert_string(new_value)
    
    def get_alarm_end_time(self):
        return self._alarm_end_time
    def set_alarm_end_time(self, new_value):
        self._alarm_end_time = convert_string(new_value)
    
    def get_mute_timeout(self):
        return self._mute_timeout
    def set_mute_timeout(self, new_value):
        self._mute_timeout = new_value
    
    def get_peer_timeout(self):
        return self._peer_timeout
    def set_peer_timeout(self, new_value):
        self._peer_timeout = new_value
    
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
            
    def get_advanced_gui_enabled(self):
        return self._logging_level == u"DEBUG"
    