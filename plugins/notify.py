from lunchinator.iface_plugins import iface_called_plugin
from lunchinator import get_settings, log_error
from lunchinator.utilities import displayNotification, drawAttention
import os

class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        self.options = [((u"icon_file", u"Icon if no avatar"),get_settings().get_resource("images", "mini_breakfast.png")),
                        ((u"audio_file", u"Audio File for Lunch Messages",self.audioFileChanged), get_settings().get_resource("sounds", "sonar.wav")),
                        ((u"open_optival_drive", "Open Optical Drive on Lunch"), True)]
        self.force_activation = True
        
    def activate(self):
        iface_called_plugin.activate(self)
    
    def deactivate(self):        
        iface_called_plugin.deactivate(self)
        
    def audioFileChanged(self,_setting,new_value):
        audio_file=self.options[u"audio_file"]
        if os.path.exists(new_value):
            audio_file = new_value
        elif os.path.exists(get_settings().get_main_config_dir()+"/sounds/"+new_value):
            audio_file= get_settings().get_main_config_dir()+"/sounds/"+new_value
        else:
            try:
                # get_resource will raise if the resource does not exist.
                audio_file = get_settings().get_resource("sounds", new_value)
            except:
                log_error("configured audio file %s does not exist in sounds folder, using old one"%new_value)
            # don't set the new value, keep old value
        return audio_file
            
    def process_message(self,msg,addr,member_info):
        name = " ["+addr+"]"
        icon = self.options[u"icon_file"]
        if member_info.has_key("avatar"):
            icon = get_settings().get_avatar_dir()+"/"+member_info["avatar"]
        if member_info.has_key("name"):
            name = " [" + member_info["name"] + "]"
        
        displayNotification(name, msg, icon)
            
    def process_lunch_call(self,_msg,_ip,_member_info):
        drawAttention(self.options["audio_file"])

    def process_event(self,cmd,value,ip,member_info):
        pass