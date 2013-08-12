from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
    
class gui_settings(iface_general_plugin):
    ls = None
    
    def __init__(self):
        super(gui_settings, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        option_names = ['user_name','audio_file','auto_update',"default_lunch_begin","default_lunch_end","alarm_begin_time","alarm_end_time","mute_timeout","tcp_port","reset_icon_time"]
        self.options = {}
        for o in option_names:
            methodname = "get_"+o
            if hasattr(self.ls, methodname): 
                _member = getattr(self.ls, methodname)
                self.options[o] = _member()
                
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