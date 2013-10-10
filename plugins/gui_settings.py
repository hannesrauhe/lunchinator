from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, log_warning
    
class gui_settings(iface_general_plugin):
    def __init__(self):
        super(gui_settings, self).__init__()
        option_names = [(u'user_name', u'User Name'),
                        (u'audio_file', u'Lunch Call Audio File'),
                        (u'auto_update', u"Automatic Update"),
                        (u"default_lunch_begin", u'Free for Lunch from'),
                        (u"default_lunch_end", u'Free for Lunch until'),
                        (u"alarm_begin_time", u"No Alarm before"),
                        (u"alarm_end_time", u"No Alarm after"),
                        (u"mute_timeout", u"Mute for x sec after Alarm"),
                        (u"reset_icon_time", u"Reset Lunchinator Icon after x min"),
                        (u"tcp_port", u"TCP Port"),
                        (u"logging_level", u"Logging Level", (u"CRITICAL", u"ERROR", u"WARNING", u"INFO", u"DEBUG")),
                        (u"group_plugins", u"Group Plugins by category")]
        self.options = []
        for o in option_names:
            methodname = "get_"+o[0]
            if hasattr(get_settings(), methodname): 
                _member = getattr(get_settings(), methodname)
                self.options.append((o, _member()))
            else:
                log_warning("settings has no attribute called '%s'" % o)
                
    def save_options_widget_data(self):
        self.save_data()
        
    def set_option_value(self, o, new_v):
        # override category as "general"
        get_settings().get_config_file().set('general', o, unicode(new_v))
        
        methodname = "set_"+o
        if hasattr(get_settings(), methodname): 
            _member = getattr(get_settings(), methodname)
            _member(self.options[o])
        else:
            log_warning("settings has no setter for '%s'" % o)
        