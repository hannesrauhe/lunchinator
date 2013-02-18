import sys,os

class lunch_default_config(object):
    audio_file ="sonar.wav"
    user_name = ""
    avatar_file = ""
    
    debug = False
    auto_update = True    
    main_config_dir = os.getenv("HOME")+"/.lunchinator"
    members_file = main_config_dir+"/lunch_members.cfg"
    avatar_dir = main_config_dir+"/avatars/"
    html_dir = main_config_dir
    
    peer_timeout = 604800 #one week so that we don't forget someone too soon
    mute_timeout = 30
    config_dirs = [sys.path[0],main_config_dir]
    icon_file = sys.path[0]+"/images/mini_breakfast.png"
    
    def __init__(self):
        if not os.path.exists(self.avatar_dir):
            os.makedirs(self.avatar_dir)
            
    def get_debug(self):
        return self.debug
        
    def set_debug(self,activate):
        if activate:
            f = open(self.main_config_dir+"/debug.cfg",'w')
            f.write("debugging activated because this file exists")
            f.close()
        else:
            os.remove(self.main_config_dir+"/debug.cfg")
        self.debug = activate
            