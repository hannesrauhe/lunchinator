from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, log_warning
    
class gui_settings(iface_general_plugin):
    def __init__(self):
        super(gui_settings, self).__init__()
        option_names = [('user_name', 'User Name'),
                        ('audio_file', 'Lunch Call Audio File'),
                        ('auto_update', "Automatic Update"),
                        ("default_lunch_begin", 'Free for Lunch from'),
                        ("default_lunch_end", 'Free for Lunch until'),
                        ("alarm_begin_time", "No Alarm before"),
                        ("alarm_end_time", "No Alarm after"),
                        ("mute_timeout", "Mute for x sec after Alarm"),
                        ("reset_icon_time", "Reset Lunchinator Icon after x min"),
                        ("tcp_port", "TCP Port"),
                        ("logging_level", "Logging Level", ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"))]
        self.options = []
        for o in option_names:
            methodname = "get_"+o[0]
            if hasattr(get_settings(), methodname): 
                _member = getattr(get_settings(), methodname)
                self.options.append((o, _member()))
            else:
                log_warning("settings has no attribute called '%s'" % o)
                
    def set_settings(self):
        for o in self.option_names:
            methodname = "set_"+o[0]
            if hasattr(get_settings(), methodname): 
                _member = getattr(get_settings(), methodname)
                _member(self.options[o[0]])
            else:
                log_warning("settings has no setter for '%s'" % o)
    
    def save_options_widget_data(self):
        # override category as "general"
        self.save_data(lambda o, new_v: get_settings().get_config_file().set('general', o, str(new_v)))
        self.set_settings()
        
    def read_options_from_file(self):
        super(gui_settings, self).read_options_from_file()
        self.set_settings()
        
        