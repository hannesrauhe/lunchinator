from lunchinator.iface_plugins import iface_called_plugin
from lunchinator import get_settings
from lunchinator.utilities import displayNotification, drawAttention

class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        self.options = {"icon_file":get_settings().get_lunchdir()+"/images/mini_breakfast.png","audio_file":get_settings().get_lunchdir()+"/sounds/sonar.wav" }
        
    def activate(self):        
        iface_called_plugin.activate(self)
            
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