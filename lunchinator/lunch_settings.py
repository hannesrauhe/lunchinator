import sys,os,getpass,ConfigParser,types,subprocess,logging
from optparse import OptionParser

'''integrate the cli-parser into the default_config sooner or later'''
from lunchinator import log_exception, log_warning, log_error,\
    log_info, setLoggingLevel
class lunch_options_parser(object):
    def parse_args(self):
        usage = "usage: %prog [options]"
        optionParser = OptionParser(usage = usage)
        optionParser.add_option("-v", "--verbose",
                          action = "store_true", dest = "verbose", default = False,
                          help = "Enable verbose output")
        optionParser.add_option("--autoUpdate",
                          default = True, dest = "noUpdates", action = "store_false",
                          help = "Automatically pull updates from Git.")
        return optionParser.parse_args()

    
class lunch_settings(object):
    _instance = None
    
    @classmethod
    def get_singleton_instance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
    
    def runGitCommand(self, args, path = None, quiet = True):
        if path == None:
            path = self.lunchdir
        
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
        self.main_config_dir = os.getenv("HOME")+os.path.sep+".lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+os.path.sep+".lunchinator"
        self.members_file = self.main_config_dir+os.path.sep+"lunch_members.cfg"
        self.messages_file = self.main_config_dir+os.path.sep+"messages"
        self.log_file = self.main_config_dir+os.path.sep+"lunchinator.log"
        self.avatar_dir = self.main_config_dir+os.path.sep+"avatars"+os.path.sep
        self.version = "unknown"
        self.version_short = "unknown"
        self.commit_count = "0"
        self.commit_count_plugins = "-1"
        self.lunchdir = sys.path[0]
        self.internal_plugin_dir = self.lunchdir+os.path.sep+"plugins"+os.path.sep
        self.external_plugin_dir = self.main_config_dir+os.path.sep+"plugins"
        self.plugin_dirs = [self.internal_plugin_dir, self.external_plugin_dir]
        
        #insert plugin folders into path
        for aDir in self.plugin_dirs:
            sys.path.insert(0, aDir)
        
        ''' not in files'''    
        self.next_lunch_begin = None
        self.next_lunch_end = None
        self.audio_file = self.lunchdir+os.path.sep+"sounds"+os.path.sep+"sonar.wav"
        self.user_name = ""
        self.avatar_file = ""    
        self.debug = False 
        self.tcp_port = 50001
        self.auto_update = True   
        self.default_lunch_begin = "12:15"
        self.default_lunch_end = "12:45"
        self.alarm_begin_time = "11:30"
        self.alarm_end_time = "13:00"
        self.peer_timeout = 604800 #one week so that we don't forget someone too soon
        self.mute_timeout = 30
        self.reset_icon_time = 5
        self.last_gui_plugin_index = 0
        self.logging_level = "ERROR"
        
        if not os.path.exists(self.main_config_dir):
            os.makedirs(self.main_config_dir)
        if not os.path.exists(self.avatar_dir):
            os.makedirs(self.avatar_dir)
        
        try:
            _, self.version, __ = self.runGitCommand(["log", "-1"], self.lunchdir, quiet=False)
            for line in self.version.splitlines():
                if line.startswith("Date:"):
                    self.version_short = line[5:].strip()            
        except:
            log_exception("git log could not be executed correctly - version information not available")
        
        try:    
            revListArgs = ["rev-list", "HEAD", "--count"]
            _, cco, __ = self.runGitCommand(revListArgs, self.lunchdir, quiet=False)
            self.commit_count = cco.strip()
            
            if os.path.exists(self.external_plugin_dir):
                retCode, cco, __ = self.runGitCommand(revListArgs, self.external_plugin_dir, quiet=False)
                if retCode == 0:
                    self.commit_count_plugins = cco.strip()
        except:
            log_exception("git rev-list could not be executed correctly - commit count information not available")
            
        self.config_file = ConfigParser.SafeConfigParser()
        self.read_config_from_hd()
            
    def read_config_from_hd(self): 
        self.config_file.read(self.main_config_dir+'/settings.cfg')
        
        self.user_name = self.read_value_from_config_file(self.user_name,"general","user_name")
        self.tcp_port = self.read_value_from_config_file(self.tcp_port,"general","tcp_port")
        
        self.auto_update = self.read_value_from_config_file(self.auto_update,"general","auto_update")
        self.default_lunch_begin = self.read_value_from_config_file(self.default_lunch_begin,"general","default_lunch_begin")
        self.default_lunch_end = self.read_value_from_config_file(self.default_lunch_end,"general","default_lunch_end")
        self.alarm_begin_time = self.read_value_from_config_file(self.alarm_begin_time,"general","alarm_begin_time")
        self.alarm_end_time = self.read_value_from_config_file(self.alarm_end_time,"general","alarm_end_time")
        
        self.peer_timeout = self.read_value_from_config_file(self.peer_timeout, "general", "peer_timeout")
        self.mute_timeout = self.read_value_from_config_file(self.mute_timeout, "general", "mute_timeout")
        self.reset_icon_time = self.read_value_from_config_file(self.reset_icon_time, "general", "reset_icon_time")
        
        self.last_gui_plugin_index = self.read_value_from_config_file(self.last_gui_plugin_index, 'general', 'last_gui_plugin_index')
        self.logging_level = self.read_value_from_config_file(self.logging_level, 'general', 'logging_level')
        
        #not shown in settings-plugin - handled by avatar-plugin
        self.avatar_file =  self.read_value_from_config_file(self.avatar_file,"general","avatar_file")
                     
        self.debug = False
                        
        if os.path.exists(self.main_config_dir+"/debug.cfg"):
            self.debug = True            
            
        if os.path.exists(self.main_config_dir+"/username.cfg"):
            with open(self.main_config_dir+"/username.cfg") as f:
                self.set_user_name(f.readline().strip())
                
        if os.path.exists(self.main_config_dir+"/avatar.cfg"):
            with open(self.main_config_dir+"/avatar.cfg") as f:
                self.set_avatar_file(f.readline().strip())
                
        if os.path.exists(self.main_config_dir+"/sound.cfg"):
            with open(self.main_config_dir+"/sound.cfg") as f:
                audio_file = f.readline().strip()
                if os.path.exists(self.main_config_dir+"/sounds/"+audio_file):
                    self.audio_file = self.main_config_dir+"/sounds/"+audio_file
                elif os.path.exists(self.lunchdir+"/sounds/"+audio_file):
                    self.audio_file = self.lunchdir+"/sounds/"+audio_file
                else:
                    log_warning("configured audio file %s does not exist in sounds folder, using old one: %s",audio_file,self.audio_file)  
        
        if self.user_name=="":
            self.user_name = getpass.getuser()  
            
    def read_value_from_config_file(self,value,section,name):
        try:
            if type(value) is types.BooleanType:
                value = self.config_file.getboolean(section,name)
            elif type(value) is types.IntType:
                value = self.config_file.getint(section,name)
            else:
                value = self.config_file.get(section,name)
        except ConfigParser.NoSectionError:
            self.config_file.add_section(section)
        except ConfigParser.NoOptionError:
            pass
        except:
            log_exception("error while reading %s from config file",name)
        return value
        
    def write_config_to_hd(self): 
        self.config_file.write(open(self.main_config_dir+'/settings.cfg','w'))
        
    def getCanUpdate(self, repo):
        if self.getGitCommandResult(["rev-parse"], repo) != 0:
            return (False, "'%s' is no git repository" % repo)
        
        if self.getGitCommandResult(["diff","--name-only","--exit-code","--quiet"], repo) != 0:
            return (False, "There are unstaged changes")
        
        if self.getGitCommandResult(["diff","--cached","--exit-code","--quiet"], repo) != 0:
            return (False, "There are staged, uncommitted changes")
        
        _, branch, __ = self.runGitCommand(["symbolic-ref","HEAD"], repo)
        if "master" not in branch:
            return (False, "The selected branch is not the master branch")
        
        if self.getGitCommandResult("log","origin/master..HEAD","--exit-code","--quiet") != 0:
            return (False, "There are unpushed commits on the master branch")
        
        return (True, None)
    
    def getCanUpdateMain(self):
        return self.getCanUpdate(self.lunchdir)
        
    def getCanUpdatePlugins(self):
        return self.getCanUpdate(self.main_config_dir + "/plugins/")
    
    #special handling for debug 
    def set_debug(self,activate):
        if activate:
            f = open(self.main_config_dir+"/debug.cfg",'w')
            f.write("debugging activated because this file exists")
            f.close()
        else:
            os.remove(self.main_config_dir+"/debug.cfg")
        self.debug = activate
        
    def get_debug(self):
        return self.debug
    
    #the rest is read from/written to the config file          
    def get_user_name(self):
        return self.user_name    
    def set_user_name(self,name,force_write=False):
        self.user_name = name
        self.config_file.set('general', 'user_name', str(name))
        if force_write:
            self.write_config_to_hd()
    
    def get_auto_update(self):
        return self.auto_update
    def set_auto_update(self, new_value):
        self.auto_update = new_value
    
    def get_audio_file(self):
        return self.audio_file 
    def set_audio_file(self, new_value):
        self.audio_file = new_value
      
    def get_avatar_dir(self):
        return self.avatar_dir
                 
    def get_avatar_file(self):
        return self.get_avatar()
    def set_avatar_file(self,file_name,force_write=False):  
        if not os.path.exists(self.avatar_dir+"/"+file_name):
            log_error("avatar does not exist: %s",file_name)
            return
        self.avatar_file = file_name
        self.config_file.set('general', 'avatar_file', str(file_name))
        if force_write:
            self.write_config_to_hd()
    
    def get_avatar(self):
        return self.avatar_file
    
    def get_default_lunch_begin(self):
        return self.default_lunch_begin
    def set_default_lunch_begin(self, new_value):
        self.default_lunch_begin = new_value
    
    def get_default_lunch_end(self):
        return self.default_lunch_end
    def set_default_lunch_end(self, new_value):
        self.default_lunch_end = new_value
    
    def get_alarm_begin_time(self):
        return self.alarm_begin_time
    def set_alarm_begin_time(self, new_value):
        self.alarm_begin_time = new_value
    
    def get_alarm_end_time(self):
        return self.alarm_end_time
    def set_alarm_end_time(self, new_value):
        self.alarm_end_time = new_value
    
    def get_mute_timeout(self):
        return self.mute_timeout
    def set_mute_timeout(self, new_value):
        self.mute_timeout = new_value
    
    def get_tcp_port(self):
        return self.tcp_port
    def set_tcp_port(self, new_value):
        self.tcp_port = new_value
    
    def get_reset_icon_time(self):
        return self.reset_icon_time
    def set_reset_icon_time(self, new_value):
        self.reset_icon_time = new_value
    
    def get_logging_level(self):
        return self.logging_level
    def set_logging_level(self, newValue):
        self.logging_level = newValue
        if newValue == "CRITICAL":
            setLoggingLevel(logging.CRITICAL)
        elif newValue == "ERROR":
            setLoggingLevel(logging.ERROR)
        elif newValue == "WARNING":
            setLoggingLevel(logging.WARNING)
        elif newValue == "INFO":
            setLoggingLevel(logging.INFO)
        elif newValue == "DEBUG":
            setLoggingLevel(logging.DEBUG)
        
    def set_last_gui_plugin_index(self, index):
        self.last_gui_plugin_index = index
        self.config_file.set('general', 'last_gui_plugin_index', str(index))
        self.write_config_to_hd()
    