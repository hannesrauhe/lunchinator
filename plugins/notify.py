from iface_called_plugin import *
from time import localtime
import subprocess,sys,ctypes
from yapsy.PluginManager import PluginManagerSingleton

class Notify(iface_called_plugin):
    def __init__(self):
        super(Notify, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def process_message(self,msg,addr,member_info):   
        print "Notify"
        if sys.platform.startswith('linux'):
            self.incoming_call_linux(msg,addr,member_info)
        else:
            self.incoming_call_win(msg,addr,member_info)
            
    def incoming_call_linux(self,msg,addr,member_info):    
        try:
            icon = self.ls.get_icon_file()
            if member_info.has_key("avatar"):
                icon = self.ls.get_avatar_dir()+"/"+member_info["avatar"]
#            print ["notify-send","--icon="+icon, msg + " [" + member_info["name"] + "]"]
            subprocess.call(["notify-send","--icon="+icon, msg + " [" + member_info["name"] + "]"])
        except:
            print "notify error"
            pass
    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765 and msg.startswith("lunch"):
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (open)"
                pass
            
            try:
                subprocess.call(["play", "-q", self.audio_file])    
            except:
                print "sound error"
                pass
        
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (close)"
                pass
        
    def incoming_call_win(self,msg,addr,member_info):    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765 and msg.startswith("lunch"):
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
        
    def process_event(self,msg,ip,member_info):
        pass