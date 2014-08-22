from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
from lunchinator import get_notification_center
from lunchinator.log import getLogger
from lunchinator.plugin import iface_general_plugin, iface_called_plugin, iface_gui_plugin, iface_db_plugin
from yapsy import PLUGIN_NAME_FORBIDEN_STRING

class NotificationPluginManager(ConfigurablePluginManager):
    def __init__(self,
                 configparser_instance=None,
                 config_change_trigger= lambda _ : True,
                 decorated_manager=None,
                 # The following args will only be used if we need to
                 # create a default PluginManager
                 categories_filter={"general" : iface_general_plugin,
                                    "called" : iface_called_plugin,
                                    "gui" : iface_gui_plugin,
                                    "db" : iface_db_plugin}, 
                 directories_list=None, 
                 plugin_info_ext="yapsy-plugin"):
        super(NotificationPluginManager, self).__init__(configparser_instance,
                                                        config_change_trigger,
                                                        decorated_manager,
                                                        categories_filter, 
                                                        directories_list, 
                                                        plugin_info_ext)
        self._emitSignals = True
    
    def __getCategoryPluginsListFromConfig(self, plugin_list_str):
        """
        Parse the string describing the list of plugins to activate,
        to discover their actual names and return them.
        """
        return plugin_list_str.strip(" ").split("%s"%PLUGIN_NAME_FORBIDEN_STRING)
    
    def loadPlugins(self, callback=None):
        self._emitSignals = False
        
        self._component.loadPlugins(callback)
        
        pluginsToLoad = set()
        # now load the plugins according to the recorded configuration
        if self.config_parser.has_section(self.CONFIG_SECTION_NAME):
            # browse all the categories
            for category_name in self._component.category_mapping.keys():
                # get the list of plugins to be activated for this
                # category
                option_name = "%s_plugins_to_load"%category_name
                if self.config_parser.has_option(self.CONFIG_SECTION_NAME,
                                                 option_name):
                    plugin_list_str = self.config_parser.get(self.CONFIG_SECTION_NAME,
                                                             option_name)
                    plugin_list = self.__getCategoryPluginsListFromConfig(plugin_list_str)
                    # activate all the plugins that should be
                    # activated
                    for plugin_name in plugin_list:
                        if plugin_name:
                            pluginsToLoad.add(plugin_name)
            
        # first, load db plugins
        # second, load remaining force activated plugins
        # last, unload regular plugins (no database, no force activation)
        loadFirst = []
        loadSecond = []
        loadThird = []            
        for pluginInfo in self.getAllPlugins():
            if pluginInfo is None or pluginInfo.plugin_object.is_activated:
                continue
            if pluginInfo.category == "db" and pluginInfo.plugin_object.force_activation:
                loadFirst.append(pluginInfo)
            elif pluginInfo.plugin_object.force_activation:
                loadSecond.append(pluginInfo)
            elif pluginInfo.name in pluginsToLoad:
                loadThird.append(pluginInfo)
                    
        for piList in (loadFirst, loadSecond, loadThird):
            for pluginInfo in piList:
                self.activatePlugin(pluginInfo=pluginInfo, save_state=False)
        
        self._emitSignals = True
    
    def activatePlugin(self, pluginInfo, save_state=True):
        getLogger().info("Activating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
        try:
            result = ConfigurablePluginManager.activatePluginByName(self, pluginInfo.name, category_name=pluginInfo.category, save_state=save_state)
            if self._emitSignals and result != None:
                get_notification_center().emitPluginActivated(pluginInfo.name, pluginInfo.category)
        except:
            getLogger().exception("Error activating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
    
    def activatePluginByName(self, plugin_name, category_name="Default", save_state=True):
        pluginInfo = self.getPluginByName(plugin_name, category_name)
        if pluginInfo is not None:
            self.activatePlugin(pluginInfo=pluginInfo, save_state=save_state)
        else:
            getLogger().error("Could not activate plugin %s of type %s (plugin not found)", plugin_name, category_name)

    def deactivatePlugins(self, pluginInfos, save_state=True):
        # first, unload regular plugins (no database, no force activation)
        # second, also unload force activated non-db plugins
        # last, unload db plugins
        unloadFirst = []
        unloadSecond = []
        unloadThird = []
        for pluginInfo in pluginInfos:
            if pluginInfo is None or not pluginInfo.plugin_object.is_activated:
                continue
            if pluginInfo.category == "db":
                unloadThird.append(pluginInfo)
            elif pluginInfo.plugin_object.force_activation:
                unloadSecond.append(pluginInfo)
            else:
                unloadFirst.append(pluginInfo)
                
        for piList in (unloadFirst, unloadSecond, unloadThird):
            # first, inform about deactivation
            for pluginInfo in piList:
                getLogger().info("Preparing to deactivate plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
                try:
                    # this is a direct connection, exception will be propagated here
                    get_notification_center().emitPluginWillBeDeactivated(pluginInfo.name, pluginInfo.category)
                except:
                    getLogger().exception("An error occured while deactivating %s", pluginInfo.name)
                        
            # then deactivate plugins
            for pluginInfo in piList:
                getLogger().info("Deactivating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
                try:
                    result = ConfigurablePluginManager.deactivatePluginByName(self, pluginInfo.name, category_name=pluginInfo.category, save_state=save_state)
                    if self._emitSignals and result != None:
                        get_notification_center().emitPluginDeactivated(pluginInfo.name, pluginInfo.category)
                except:
                    getLogger().exception("An error occured while deactivating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)

    def deactivatePluginByName(self, plugin_name, category_name="Default", save_state=True):
        pluginInfo = self.getPluginByName(plugin_name, category_name)
        if pluginInfo is not None:
            self.deactivatePlugins([pluginInfo], save_state=save_state)
        else:
            getLogger().error("Could not deactivate plugin %s from category (plugin not found)", plugin_name, category_name)
