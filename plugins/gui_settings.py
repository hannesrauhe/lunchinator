from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_server, get_settings, log_warning
    
class gui_settings(iface_general_plugin):
    def __init__(self):
        super(gui_settings, self).__init__()
        option_names = [(u'user_name', u'User Name'),
                        (u'lunch_trigger', u'Word that triggers alarm'),
                        (u'group', u'Group Name', self.change_group),
                        (u"default_lunch_begin", u'Free for Lunch from'),
                        (u"default_lunch_end", u'Free for Lunch until'),
                        (u"warn_if_members_not_ready", u"Warn if members are not ready for lunch"),
                        (u"alarm_begin_time", u"No Alarm before"),
                        (u"alarm_end_time", u"No Alarm after"),
                        (u"mute_timeout", u"Mute for x sec after Alarm"),
                        (u"reset_icon_time", u"Reset Lunchinator Icon after x min"),
                        (u"tcp_port", u"TCP Port"),
                        (u"logging_level", u"Logging Level", (u"CRITICAL", u"ERROR", u"WARNING", u"INFO", u"DEBUG")),
                        (u"group_plugins", u"Group Plugins by category", self._requires_restart_callback),
                        (u"proxy", u"Proxy Server (usually detected automatically)")]
        self.options = []
        self.force_activation = True
        for o in option_names:
            val = self._get_option_value(o[0])
            if val != None:
                self.options.append((o, val))
                
    def save_options_widget_data(self):
        self.save_data()
        
    def _get_option_value(self, oname):
        methodname = "get_"+oname
        if hasattr(get_settings(), methodname): 
            _member = getattr(get_settings(), methodname)
            return _member()
        else:
            log_warning("settings has no attribute called '%s'" % oname)
        return None
        
    def set_option_value(self, o, new_v):
        # override category as "general"
        get_settings().get_config_file().set('general', o, unicode(new_v))
        
        methodname = "set_"+o
        if hasattr(get_settings(), methodname): 
            _member = getattr(get_settings(), methodname)
            _member(self.options[o])
        else:
            log_warning("settings has no setter for '%s'" % o)
        
        return self._get_option_value(o)
            
    def change_group(self, _key, value):
        get_server().changeGroup(unicode(value))