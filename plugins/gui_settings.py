from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import get_settings, get_notification_center, convert_string
from lunchinator.lunch_settings import lunch_settings
    
class gui_settings(iface_general_plugin):
    def __init__(self):
        super(gui_settings, self).__init__()
        self.options = lunch_settings.get_general_settings()
        self.force_activation = True
                
    def activate(self):
        iface_general_plugin.activate(self)
        get_notification_center().connectGeneralSettingChanged(self._settingChanged)
        
    def deactivate(self):
        get_notification_center().disconnectGeneralSettingChanged(self._settingChanged)
        iface_general_plugin.deactivate(self)

    def save_options_widget_data(self):
        get_notification_center().disconnectGeneralSettingChanged(self._settingChanged)
        super(gui_settings, self).save_options_widget_data()
        get_notification_center().connectGeneralSettingChanged(self._settingChanged)
    
    """ Overrides to change options data source """
    
    def _getOptionValue(self, o, _hidden=False):
        return get_settings().get_option(o)
    
    def _callOptionCallback(self, o, new_v):
        return get_settings().set_option(o, new_v)
    
    def _initOptionValue(self, o, v, _hidden=False):
        # initializing done in lunch_settings
        pass
    
    def _setOptionValue(self, o, v, _hidden=False):
        # nothing to do here, already set in option callback (setter).
        pass
    
    def _iterOptions(self, _hidden=False):
        """Iterates over (option key, option value)"""
        for option in self.options:
            yield (option, get_settings().get_option(option))
    
    def _hasConfigOption(self, _o):
        # config options managed in lunch_settings
        return False
    
    def _getConfigOption(self, _o):
        # config options managed in lunch_settings
        return None
        
    def _setConfigOption(self, _o, _v):
        # config options managed in lunch_settings
        pass
    
    """ End overrides """
    
    def _settingChanged(self, settingName):
        settingName = convert_string(settingName)
        self._displayOptionValue(settingName)
