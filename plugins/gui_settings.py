from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
    
class gui_settings(iface_general_plugin):
    ls = None
    
    def __init__(self):
        super(gui_settings, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        option_names = [('user_name', 'User Name'),
                        ('audio_file', 'Lunch Call Audio File'),
                        ('auto_update', "Automatic Update"),
                        ("default_lunch_begin", 'Free for Lunch from'),
                        ("default_lunch_end", 'Free for Lunch until'),
                        ("alarm_begin_time", "No Alarm before"),
                        ("alarm_end_time", "No Alarm after"),
                        ("mute_timeout", "Mute for x sec after Alarm"),
                        ("Reset Lunchinator Icon after x min", ""),
                        ("tcp_port", "TCP Port")]
        self.options = []
        for o in option_names:
            methodname = "get_"+o[0]
            if hasattr(self.ls, methodname): 
                _member = getattr(self.ls, methodname)
                self.options.append((o, _member()))
                
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
                self.ls.config_file.set('general', o, str(new_v))
        self.discard_options_widget_data()
        self.ls.write_config_to_hd()
        self.ls.read_config_from_hd()