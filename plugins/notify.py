from lunchinator.iface_plugins import *
from time import localtime
import subprocess,sys,ctypes
from lunchinator import get_server, log_exception, get_settings

class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        self.options = {"icon_file":get_settings().lunchdir+"/images/mini_breakfast.png","audio_file":get_settings().lunchdir+"/sounds/sonar.wav" }
        
    def activate(self):        
        iface_called_plugin.activate(self)
            
    def process_message(self,msg,addr,member_info):
        name = " ["+addr+"]"    
        if sys.platform.startswith('linux'):
            try:
                icon = self.options["icon_file"]
                if member_info.has_key("avatar"):
                    icon = get_settings().get_avatar_dir()+"/"+member_info["avatar"]
    #            print ["notify-send","--icon="+icon, msg + " [" + member_info["name"] + "]"]
                if member_info.has_key("name"):
                    name = " [" + member_info["name"] + "]"
                subprocess.call(["notify-send","--icon="+icon, name, msg])
            except:
                log_exception("notify error: %s"%str(sys.exc_info()))
        elif "darwin" in sys.platform:
            try:
                subprocess.call(["terminal-notifier", "-title", "Lunchinator: %s" % name, "-message", msg])
            except:
                log_exception("error sending notification")
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
            log_exception("notify error: eject error (open)")
        
        try:
            subprocess.call(["play", "-q", self.options["audio_file"]])    
        except:
            log_exception("notify error: sound error")
    
        try:
            subprocess.call(["eject", "-T", "/dev/cdrom"])
        except:
            log_exception("notify error: eject error (close)")
            
    def incoming_call_mac(self,msg,addr,member_info):      
        try:
            subprocess.call(["drutil", "tray", "eject"])
        except:
            log_exception("notify error: eject error (open)")
             
        try:
            subprocess.call(["afplay", self.options["audio_file"]])    
        except:
            log_exception("notify error: sound error")
             
        try:
            subprocess.call(["drutil", "tray", "close"])
        except:
            log_exception("notify error: eject error (close)")
    
    def incoming_call_win(self,msg,addr,member_info):    
        try:
            ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
        except:
            log_exception("notify error: eject error (open)")
        try:
            ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
        except:
            log_exception("notify error: eject error (close)")

    def process_event(self,cmd,value,ip,member_info):
        pass