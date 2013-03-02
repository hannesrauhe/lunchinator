import sys,os,getpass,ConfigParser,types,subprocess,logging

class lunch_default_config(object):
    '''unchangeable for now'''
    main_config_dir = os.getenv("HOME")+"/.lunchinator"
    icon_file = sys.path[0]+"/images/mini_breakfast.png"
    members_file = main_config_dir+"/lunch_members.cfg"
    messages_file = main_config_dir+"/messages"
    avatar_dir = main_config_dir+"/avatars/"
    html_dir = main_config_dir
    version = "unknown"
    version_short = "unknown"
    plugin_dirs = [main_config_dir+"/plugins",sys.path[0]+"/plugins"]
    
    ''' not in files'''    
    next_lunch_begin = "12:15"
    next_lunch_end = "12:45"
    
    '''changed by using files'''
    audio_file = sys.path[0]+"/sounds/sonar.wav"
    user_name = ""
    avatar_file = ""    
    debug = False 
    http_server = False
    
    '''file settings.cfg standard section '''
    auto_update = True   
    default_lunch_begin = "12:15"
    default_lunch_end = "12:45"
    alarm_begin_time = "11:30"
    alarm_end_time = "13:00"
    
    '''file settings.cfg advanced section '''
    http_port = 50002
    peer_timeout = 604800 #one week so that we don't forget someone too soon
    mute_timeout = 30
    
    def __init__(self):
        if not os.path.exists(self.avatar_dir):
            os.makedirs(self.avatar_dir)
        try:
            os.chdir(sys.path[0])
            p = subprocess.Popen(["git","log","-1"],stdout=subprocess.PIPE)
            self.version, err = p.communicate()
            self.version_short = self.version.splitlines()[2][5:].strip()
        except:
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
        
        self.http_port = self.read_value_from_config_file(self.http_port, "advanced", "http_port")
        self.peer_timeout = self.read_value_from_config_file(self.peer_timeout, "advanced", "peer_timeout")
        self.mute_timeout = self.read_value_from_config_file(self.mute_timeout, "advanced", "mute_timeout")
                     
        self.debug = False
        self.http_server = False
                        
        if os.path.exists(self.main_config_dir+"/debug.cfg"):
            self.debug = True            
            
        if os.path.exists(self.main_config_dir+"/http_server.cfg"):
            self.http_server = True
            
        if os.path.exists(self.main_config_dir+"/username.cfg"):
            with open(self.main_config_dir+"/username.cfg") as f:
                self.set_user_name(f.readline().strip())
                
        if os.path.exists(self.main_config_dir+"/avatar.cfg"):
            with open(self.main_config_dir+"/avatar.cfg") as f:
                self.avatar_file = f.readline().strip()
                
        if os.path.exists(self.main_config_dir+"/sound.cfg"):
            with open(self.main_config_dir+"/sound.cfg") as f:
                audio_file = f.readline().strip()
                if os.path.exists(self.main_config_dir+"/sounds/"+audio_file):
                    self.audio_file = self.main_config_dir+"/sounds/"+audio_file
                elif os.path.exists(sys.path[0]+"/sounds/"+audio_file):
                    self.audio_file = sys.path[0]+"/sounds/"+audio_file
                else:
                    print "configured audio file "+audio_file+" does not exist in sounds folder, using old one: "+self.audio_file  
        
        if self.user_name=="":
            self.user_name = getpass.getuser()  
        
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.ERROR)
            
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
            if self.debug:
                print "error while reading",name,"from config file"
            else:
                pass
        if self.debug:
            print name,value
        return value
        
    def write_config_to_hd(self): 
        self.config_file.write(open(self.main_config_dir+'/settings.cfg','w'))
            
    def get_debug(self):
        return self.debug
        
    def get_http_server(self):
        return self.http_server
        
    def get_user_name(self):
        return self.user_name
    
    def get_icon_file(self):
        return self.icon_file

    def get_avatar_dir(self):
        return self.avatar_dir
        
    def get_avatar(self):
        return self.avatar_file
        
    def set_user_name(self,name,force_write=False):
        self.user_name = name
        self.config_file.set('general', 'user_name', str(name))
        if not force_write:
            self.write_config_to_hd()
        
    def set_debug(self,activate):
        if activate:
            f = open(self.main_config_dir+"/debug.cfg",'w')
            f.write("debugging activated because this file exists")
            f.close()
        else:
            os.remove(self.main_config_dir+"/debug.cfg")
        self.debug = activate
        
    def set_http_server(self,activate):
        if activate:
            f = open(self.main_config_dir+"/http_server.cfg",'w')
            f.write("Http Server will run on port: "+str(self.http_port)+" because this file exists")
            f.close()
        else:
            os.remove(self.main_config_dir+"/http_server.cfg")
        self.http_server = activate
            
    