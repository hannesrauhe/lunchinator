from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
from lunchinator import get_notification_center
from lunchinator.log import getCoreLogger
from lunchinator.plugin import iface_general_plugin, iface_called_plugin, iface_gui_plugin, iface_db_plugin
from yapsy import PLUGIN_NAME_FORBIDEN_STRING
from lunchinator.utilities import INSTALL_SUCCESS, INSTALL_FAIL,\
    INSTALL_CANCEL, INSTALL_RESTART, INSTALL_IGNORE

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

    def __getCategoryPluginsConfigFromList(self, plugin_list):
        """
        Compose a string describing the list of plugins to activate
        """
        return PLUGIN_NAME_FORBIDEN_STRING.join(plugin_list)
        
    def __getCategoryOptionsName(self,category_name):
        """
        Return the appropirately formated version of the category's
        option.
        """
        return "%s_plugins_to_load" % category_name.replace(" ","_")

    def __addPluginToConfig(self,category_name, plugin_name):
        """
        Utility function to add a plugin to the list of plugin to be
        activated.
        """
        # check that the section is here
        if not self.config_parser.has_section(self.CONFIG_SECTION_NAME):
            self.config_parser.add_section(self.CONFIG_SECTION_NAME)
        # check that the category's list of activated plugins is here too
        option_name = self.__getCategoryOptionsName(category_name)
        if not self.config_parser.has_option(self.CONFIG_SECTION_NAME, option_name):
            # if there is no list yet add a new one
            self.config_parser.set(self.CONFIG_SECTION_NAME,option_name,plugin_name)
            return self.config_has_changed()
        else:
            # get the already existing list and append the new
            # activated plugin to it.
            past_list_str = self.config_parser.get(self.CONFIG_SECTION_NAME,option_name)
            past_list = self.__getCategoryPluginsListFromConfig(past_list_str)
            # make sure we don't add it twice
            if plugin_name not in past_list: 
                past_list.append(plugin_name)
                new_list_str = self.__getCategoryPluginsConfigFromList(past_list)
                self.config_parser.set(self.CONFIG_SECTION_NAME,option_name,new_list_str)
                return self.config_has_changed()

    def __removePluginFromConfig(self,category_name, plugin_name):
        """
        Utility function to add a plugin to the list of plugin to be
        activated.
        """
        # check that the section is here
        if not self.config_parser.has_section(self.CONFIG_SECTION_NAME):
            # then nothing to remove :)
            return 
        # check that the category's list of activated plugins is here too
        option_name = self.__getCategoryOptionsName(category_name)
        if not self.config_parser.has_option(self.CONFIG_SECTION_NAME, option_name):
            # if there is no list still nothing to do
            return
        else:
            # get the already existing list
            past_list_str = self.config_parser.get(self.CONFIG_SECTION_NAME,option_name)
            past_list = self.__getCategoryPluginsListFromConfig(past_list_str)
            if plugin_name in past_list:
                past_list.remove(plugin_name)
                new_list_str = self.__getCategoryPluginsConfigFromList(past_list)
                self.config_parser.set(self.CONFIG_SECTION_NAME,option_name,new_list_str)
                self.config_has_changed()        
            

    
    def loadPlugins(self, callback=None):
        from lunchinator.utilities import handleMissingDependencies
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

        missing = {}
        for piList in (loadFirst, loadSecond, loadThird):
            newMissing = self.checkActivation(piList)
            missing.update(newMissing)
            
        from lunchinator import get_server
        result = handleMissingDependencies(missing)
        if result == INSTALL_FAIL:
            # maybe there were dependencies installed, better re-check
            missing = {}
            for piList in (loadFirst, loadSecond, loadThird):
                newMissing = self.checkActivation(piList)
                missing.update(newMissing)
            self._deactivateMissing(missing)
        elif result == INSTALL_CANCEL:
            # user chose not to install -> deactivate
            self._deactivateMissing(missing)
        elif result in (INSTALL_SUCCESS, INSTALL_IGNORE):
            missing = {}
        elif result == INSTALL_RESTART:
            return
                    
        for piList in (loadFirst, loadSecond, loadThird):
            for pluginInfo in piList:
                if (pluginInfo.name, pluginInfo.category) in missing:
                    self._logCannotLoad(pluginInfo, missing)
                    continue
                self.activatePlugin(pluginInfo=pluginInfo, save_state=False, checkDependencies=False)
        
        self._emitSignals = True
        
    def _deactivateMissing(self, missing):
        for component in missing.keys():
            pluginName, category = component
            pluginInfo = self._component.getPluginByName(pluginName, category)
            try:
                self.__removePluginFromConfig(pluginInfo.category, pluginInfo.name)
            except:
                getCoreLogger().exception("Error removing plugin %s (%s) from list of plugins to load", pluginInfo.name, pluginInfo.category)
        
    def checkActivation(self, plugins):
        missing = {}
        for pluginInfo in plugins:
            if pluginInfo.details.has_option("Requirements", "pip"):
                from lunchinator.utilities import checkRequirements
                checkRequirements(pluginInfo.details.get("Requirements", "pip").split(";;"),
                                  (pluginInfo.name, pluginInfo.category),
                                  pluginInfo.plugin_object.get_displayed_name(),
                                  missing)
        return missing
    
    def _logCannotLoad(self, pluginInfo, missing):
        getCoreLogger().warning("Cannot load plugin %s: Missing dependencies (%s)",
                                pluginInfo.plugin_object.get_displayed_name(),
                                [tup[1] for tup in missing.values()[0]])
    
    def activatePlugin(self, pluginInfo, save_state=True, checkDependencies=True):
        from lunchinator.utilities import handleMissingDependencies
        from lunchinator import get_server
        
        if checkDependencies:
            missing = self.checkActivation([pluginInfo])
            result = handleMissingDependencies(missing)
            if result == INSTALL_FAIL:
                # maybe there were dependencies installed, better re-check
                missing = self.checkActivation([pluginInfo])
                if missing:
                    self._logCannotLoad(pluginInfo, missing)
                    get_notification_center().emitPluginDeactivated(pluginInfo.name, pluginInfo.category)
                    return
            elif result == INSTALL_CANCEL:
                # user chose not to install -> deactivate
                get_notification_center().emitPluginDeactivated(pluginInfo.name, pluginInfo.category)
                self._deactivateMissing(missing)
                return
            elif result in (INSTALL_SUCCESS, INSTALL_IGNORE):
                missing = {}
            elif result == INSTALL_RESTART:
                # store that the plugin is activated now
                self.__addPluginToConfig(pluginInfo.category, pluginInfo.name)
                return
        
        getCoreLogger().info("Activating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
        try:
            pluginInfo.plugin_object.setPluginName(pluginInfo.name)
            result = ConfigurablePluginManager.activatePluginByName(self, pluginInfo.name, category_name=pluginInfo.category, save_state=save_state)
            if self._emitSignals and result != None:
                get_notification_center().emitPluginActivated(pluginInfo.name, pluginInfo.category)
        except:
            getCoreLogger().exception("Error activating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
    
    def activatePluginByName(self, plugin_name, category_name="Default", save_state=True):
        pluginInfo = self.getPluginByName(plugin_name, category_name)
        if pluginInfo is not None:
            self.activatePlugin(pluginInfo=pluginInfo, save_state=save_state)
        else:
            getCoreLogger().error("Could not activate plugin %s of type %s (plugin not found)", plugin_name, category_name)

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
                getCoreLogger().info("Preparing to deactivate plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
                try:
                    # this is a direct connection, exception will be propagated here
                    get_notification_center().emitPluginWillBeDeactivated(pluginInfo.name, pluginInfo.category)
                except:
                    getCoreLogger().exception("An error occured while deactivating %s", pluginInfo.name)
                        
            # then deactivate plugins
            for pluginInfo in piList:
                getCoreLogger().info("Deactivating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)
                try:
                    result = ConfigurablePluginManager.deactivatePluginByName(self, pluginInfo.name, category_name=pluginInfo.category, save_state=save_state)
                    if self._emitSignals and result != None:
                        get_notification_center().emitPluginDeactivated(pluginInfo.name, pluginInfo.category)
                except:
                    getCoreLogger().exception("An error occured while deactivating plugin '%s' of type '%s'", pluginInfo.name, pluginInfo.category)

    def deactivatePluginByName(self, plugin_name, category_name="Default", save_state=True):
        pluginInfo = self.getPluginByName(plugin_name, category_name)
        if pluginInfo is not None:
            self.deactivatePlugins([pluginInfo], save_state=save_state)
        else:
            getCoreLogger().error("Could not deactivate plugin %s from category (plugin not found)", plugin_name, category_name)
