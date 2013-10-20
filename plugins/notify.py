from lunchinator.iface_plugins import iface_called_plugin
from lunchinator import get_settings, log_error
from lunchinator.utilities import displayNotification, drawAttention
import os

class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        self.options = [((u"icon_file", u"Icon if no avatar"),get_settings().get_lunchdir()+"/images/mini_breakfast.png"),
                        ((u"audio_file", u"Audio File for Lunch Messages",self.audioFileChanged), get_settings().get_lunchdir()+"/sounds/sonar.wav"),
                        ((u"open_optival_drive", "Open Optical Drive on Lunc"), True)]
        
    def activate(self):
        iface_called_plugin.activate(self)
    
    def deactivate(self):        
        iface_called_plugin.deactivate(self)
        
    def audioFileChanged(self,setting,new_value):
        audio_file=''
        if os.path.exists(new_value):
            audio_file = new_value
        elif os.path.exists(get_settings().get_main_config_dir()+"/sounds/"+new_value):
            audio_file= get_settings().get_main_config_dir()+"/sounds/"+new_value
        elif os.path.exists(get_settings().get_lunchdir()+"/sounds/"+new_value):
            audio_file = get_settings().get_lunchdir()+"/sounds/"+new_value
        else:
            log_error("configured audio file %s does not exist in sounds folder, using old one"%new_value)
            #returning false just resets the value
            return False
        self.set_option(setting, audio_file)
            
    def process_message(self,msg,addr,member_info):
        name = " ["+addr+"]"
        icon = self.options["icon_file"]
        if member_info.has_key("avatar"):
            icon = get_settings().get_avatar_dir()+"/"+member_info["avatar"]
        if member_info.has_key("name"):
            name = " [" + member_info["name"] + "]"
        
        displayNotification(name, msg, icon)
            
    def process_lunch_call(self,_msg,_ip,_member_info):
        drawAttention(self.options["audio_file"])

    def process_event(self,cmd,value,ip,member_info):
        pass