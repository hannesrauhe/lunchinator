from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
from yapsy.IPlugin import IPlugin
from lunchinator import get_notification_center, log_info

class NotificationPluginManager(ConfigurablePluginManager):
    def __init__(self,
                 configparser_instance=None,
                 config_change_trigger= lambda x:True,
                 decorated_manager=None,
                 # The following args will only be used if we need to
                 # create a default PluginManager
                 categories_filter={"Default":IPlugin}, 
                 directories_list=None, 
                 plugin_info_ext="yapsy-plugin"):
        super(NotificationPluginManager, self).__init__(configparser_instance,
                                                        config_change_trigger,
                                                        decorated_manager,
                                                        categories_filter, 
                                                        directories_list, 
                                                        plugin_info_ext)
        self._emitSignals = True
    
    def loadPlugins(self, callback=None):
        self._emitSignals = False
        ConfigurablePluginManager.loadPlugins(self, callback=callback)
        self._emitSignals = True
    
    def activatePluginByName(self, plugin_name, category_name="Default", save_state=True, emit=True):
        log_info("Activating plugin '%s' of type '%s'" % (plugin_name, category_name))
        result = ConfigurablePluginManager.activatePluginByName(self, plugin_name, category_name=category_name, save_state=save_state)
        if emit and self._emitSignals and result != None:
            get_notification_center().emitPluginActivated(plugin_name, category_name)
        return result
    
    def deactivatePluginByName(self, plugin_name, category_name="Default", save_state=True, emit=True):
        log_info("Deactivating plugin '%s' of type '%s'" % (plugin_name, category_name))
        result = ConfigurablePluginManager.deactivatePluginByName(self, plugin_name, category_name=category_name, save_state=save_state)
        if emit and self._emitSignals and result != None:
            get_notification_center().emitPluginDeactivated(plugin_name, category_name)
        return result
