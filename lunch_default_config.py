import sys,os,getpass

class lunch_default_config(object):
    audio_file = sys.path[0]+"/sounds/sonar.wav"
    user_name = ""
    avatar_file = ""
    
    debug = False
    auto_update = True    
    main_config_dir = os.getenv("HOME")+"/.lunchinator"
    members_file = main_config_dir+"/lunch_members.cfg"
    messages_file = main_config_dir+"/messages"
    avatar_dir = main_config_dir+"/avatars/"
    html_dir = main_config_dir
    http_server = False
    http_port = 50002
    show_pic_fallback = sys.path[0]+"/images/webcam.jpg"
    show_pic_url = "http://webcam.wdf.sap.corp:1080/images/canteen_bac.jpeg"
    
    peer_timeout = 604800 #one week so that we don't forget someone too soon
    mute_timeout = 30
    icon_file = sys.path[0]+"/images/mini_breakfast.png"
    
    def __init__(self):
        if not os.path.exists(self.avatar_dir):
            os.makedirs(self.avatar_dir)
        self.read_config_from_hd()
            
    def read_config_from_hd(self):                     
        self.debug = False
        self.http_server = False
                        
        if os.path.exists(self.main_config_dir+"/debug.cfg"):
            self.debug = True            
            
        if os.path.exists(self.main_config_dir+"/http_server.cfg"):
            self.http_server = True
            
        if os.path.exists(self.main_config_dir+"/username.cfg"):
            with open(self.main_config_dir+"/username.cfg") as f:
                self.user_name = f.readline().strip()
                
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
            
    def get_debug(self):
        return self.debug
        
    def get_http_server(self):
        return self.http_server
        
    def get_user_name(self):
        return self.user_name
        
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
        
    def get_avatar(self):
        return self.avatar_file
            