import sys,os,getpass,ConfigParser,types,subprocess,logging

class lunch_default_config(object):
    '''unchangeable for now'''
    main_config_dir = os.getenv("HOME")+"/.lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+"/.lunchinator"
    members_file = main_config_dir+"/lunch_members.cfg"
    messages_file = main_config_dir+"/messages"
    log_file = main_config_dir+"/lunchinator.log"
    avatar_dir = main_config_dir+"/avatars/"
    version = "unknown"
    version_short = "unknown"
    plugin_dirs = [main_config_dir+"/plugins",sys.path[0]+"/plugins"]
    
    ''' not in files'''    
    next_lunch_begin = None
    next_lunch_end = None
    
    '''changed by using files'''
    audio_file = sys.path[0]+"/sounds/sonar.wav"
    user_name = ""
    avatar_file = ""    
    debug = False 
    
    '''file settings.cfg standard section '''
    auto_update = True   
    default_lunch_begin = "12:15"
    default_lunch_end = "12:45"
    alarm_begin_time = "11:30"
    alarm_end_time = "13:00"
    peer_timeout = 604800 #one week so that we don't forget someone too soon
    mute_timeout = 30
    
    def __init__(self):
        if not os.path.exists(self.main_config_dir):
            os.makedirs(self.main_config_dir)
        if not os.path.exists(self.avatar_dir):
            os.makedirs(self.avatar_dir)
        logging.basicConfig(filename=self.log_file,level=logging.WARNING)
        try:
            os.chdir(sys.path[0])
            p = subprocess.Popen(["git","log","-1"],stdout=subprocess.PIPE)
            self.version, err = p.communicate()
            self.version_short = self.version.splitlines()[2][5:].strip()
        except:
            logging.warn("git log could not be executed correctly - version information not available")
            pass
        self.config_file = ConfigParser.SafeConfigParser()
        self.read_config_from_hd()
            
    def read_config_from_hd(self): 
        self.config_file.read(self.main_config_dir+'/settings.cfg')
        
        self.user_name = self.read_value_from_config_file(self.user_name,"general","user_name")
        
        self.auto_update = self.read_value_from_config_file(self.auto_update,"general","auto_update")
        self.default_lunch_begin = self.read_value_from_config_file(self.default_lunch_begin,"general","default_lunch_begin")
        self.default_lunch_end = self.read_value_from_config_file(self.default_lunch_end,"general","default_lunch_end")
        self.alarm_begin_time = self.read_value_from_config_file(self.alarm_begin_time,"general","alarm_begin_time")
        self.alarm_end_time= self.read_value_from_config_file(self.alarm_end_time,"general","alarm_end_time")
        
        self.peer_timeout = self.read_value_from_config_file(self.peer_timeout, "general", "peer_timeout")
        self.mute_timeout = self.read_value_from_config_file(self.mute_timeout, "general", "mute_timeout")
                     
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
                elif os.path.exists(sys.path[0]+"/sounds/"+audio_file):
                    self.audio_file = sys.path[0]+"/sounds/"+audio_file
                else:
                    logging.warn("configured audio file %s does not exist in sounds folder, using old one: %s",audio_file,self.audio_file)  
        
        if self.user_name=="":
            self.user_name = getpass.getuser()  
        
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)
            
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
            logging.error("error while reading %s from config file",name)
        return value
        
    def write_config_to_hd(self): 
        self.config_file.write(open(self.main_config_dir+'/settings.cfg','w'))
        
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
    def get_auto_update(self):
        return self.auto_update    
    def get_audio_file(self):
        return self.audio_file    
    def get_icon_file(self):
        return self.icon_file
    def get_avatar_dir(self):
        return self.avatar_dir        
    def get_avatar_file(self):
        return self.get_avatar()
    def get_avatar(self):
        return self.avatar_file
    def get_default_lunch_begin(self):
        return self.default_lunch_begin
    def get_default_lunch_end(self):
        return self.default_lunch_end
    def get_alarm_begin_time(self):
        return self.alarm_begin_time
    def get_alarm_end_time(self):
        return self.alarm_end_time
    def get_mute_timeout(self):
        return self.mute_timeout
    
    def set_user_name(self,name,force_write=False):
        self.user_name = name
        self.config_file.set('general', 'user_name', str(name))
        if force_write:
            self.write_config_to_hd()
        
    def set_avatar_file(self,file_name,force_write=False):  
        if not os.path.exists(self.avatar_dir+"/"+file_name):
            logging.error("avatar does not exist: %s",file_name)
            return
        self.avatar_file = file_name
        self.config_file.set('general', 'avatar_file', str(file_name))
        #legacy: write the filename to the avatar.cfg if user still has that
        if os.path.exists(self.main_config_dir+"/avatar.cfg"):
            with open(self.main_config_dir+"/avatar.cfg",'w') as f:
                f.write(file_name)
        if force_write:
            self.write_config_to_hd()
        
            
    