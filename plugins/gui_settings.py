from lunchinator.iface_plugins import *
from lunchinator import get_server, get_settings
    
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
                        ("tcp_port", "TCP Port")]
        self.options = []
        for o in option_names:
            methodname = "get_"+o[0]
            if hasattr(get_settings(), methodname): 
                _member = getattr(get_settings(), methodname)
                self.options.append((o, _member()))
            else:
                log_warning("settings has no attribute called '%s'" % o)
                
    def save_options_widget_data(self):
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            v = self.options[o]
            new_v = v
            if type(v)==types.IntType:
                new_v = e.get_value_as_int()
            elif type(v)==types.BooleanType:
                new_v = e.get_active()
            else:
                new_v = e.get_text()
            if new_v!=v:
                self.options[o]=new_v
                #TODO(Hannes) hack
                get_settings().config_file.set('general', o, str(new_v))
        self.discard_options_widget_data()
        get_settings().write_config_to_hd()
        get_settings().read_config_from_hd()