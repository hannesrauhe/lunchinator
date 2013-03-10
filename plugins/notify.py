
from iface_plugins import *
from time import localtime
import subprocess,sys,ctypes
from yapsy.PluginManager import PluginManagerSingleton

class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):        
        iface_called_plugin.activate(self)
        if not self.hasConfigOption("icon_file"):
            self.setConfigOption("icon_file",sys.path[0]+"/images/mini_breakfast.png" )
            
    def process_message(self,msg,addr,member_info):
        if sys.platform.startswith('linux'):    
            try:
                icon = self.getConfigOption("icon_file")
                name = " ["+addr+"]"
                if member_info.has_key("avatar"):
                    icon = self.ls.get_avatar_dir()+"/"+member_info["avatar"]
    #            print ["notify-send","--icon="+icon, msg + " [" + member_info["name"] + "]"]
                if member_info.has_key("name"):
                    name = " [" + member_info["name"] + "]"
                subprocess.call(["notify-send","--icon="+icon, msg + name])
            except:
                print "notify error",sys.exc_info()[0]
        else:
            self.incoming_call_win(msg,addr,member_info)
            
    def process_lunch_call(self,msg,ip,member_info):
        if sys.platform.startswith('linux'):
            self.incoming_call_linux(msg,ip,member_info)
        else:
            self.incoming_call_win(msg,ip,member_info)
            
    def incoming_call_linux(self,msg,addr,member_info):       
        try:
            subprocess.call(["eject", "-T", "/dev/cdrom"])
        except:
            print "eject error (open)"
            pass
        
        try:
            subprocess.call(["play", "-q", self.ls.audio_file])    
        except:
            print "sound error"
            pass
    
        try:
            subprocess.call(["eject", "-T", "/dev/cdrom"])
        except:
            print "eject error (close)"
            pass
        
    def incoming_call_win(self,msg,addr,member_info):    
        try:
            ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
        except:
            print "eject error (open)"
            pass
        try:
            ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
        except:
            print "eject error (close)"
            pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass