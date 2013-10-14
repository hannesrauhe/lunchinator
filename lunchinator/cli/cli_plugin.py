import shlex
from functools import partial
from lunchinator.cli import LunchCLIModule
from lunchinator import get_server, log_exception

class CLIPluginHandling(LunchCLIModule):
    def __init__(self, parent):
        super(CLIPluginHandling, self).__init__()
        self.parent = parent
    
    def getPluginNames(self, listActivated, listDeactivated, category = None):
        try:
            plugins = None
            if category == None:
                plugins = get_server().plugin_manager.getAllPlugins()
            else:
                plugins = get_server().plugin_manager.getPluginsOfCategory(category)
            
            for pluginInfo in plugins:
                if pluginInfo.plugin_object.is_activated and listActivated or\
                        not pluginInfo.plugin_object.is_activated and listDeactivated:
                    yield (pluginInfo.name, pluginInfo.description, pluginInfo.categories)
        except:
            log_exception("while collecting option categories")
            
    def listPlugins(self, args):
        try:
            category = None
            if len(args) > 0:
                category = args[0]
            self.appendOutput("Loaded", "Category", "Name", "Description")
            self.appendSeparator()
            for name, desc, cats in sorted(self.getPluginNames(True, False, category), key=lambda aTuple : aTuple[0]):
                self.appendOutput("yes", cats, name, desc)
            for name, desc, cats in sorted(self.getPluginNames(False, True, category), key=lambda aTuple : aTuple[0]):
                self.appendOutput("no", cats, name, desc)
            self.flushOutput()
        except:
            log_exception("while printing plugin names")
            
    def loadPlugins(self, args):
        while len(args) > 0:
            pluginName = args.pop(0).upper()
            try:
                pInfo = None
                for pluginInfo in get_server().plugin_manager.getAllPlugins():
                    if pluginInfo.name.upper() == pluginName:
                        pInfo = pluginInfo
                if pInfo == None:
                    print "Unknown plugin. The available plugins are:"
                    self.listPlugins(args)
                elif pInfo.plugin_object.is_activated:
                    print "Plugin already loaded."
                else:
                    po = get_server().plugin_manager.activatePluginByName(pInfo.name,pInfo.categories[0])
                    self.parent.addModule(po)
            except:
                log_exception("while loading plugin")
            
    def unloadPlugins(self, args):
        while len(args) > 0:
            pluginName = args.pop(0).upper()
            try:
                pInfo = None
                for pluginInfo in get_server().plugin_manager.getAllPlugins():
                    if pluginInfo.name.upper() == pluginName:
                        pInfo = pluginInfo
                if pInfo == None:
                    print "Unknown plugin. The available plugins are:"
                    self.listPlugins(args)
                elif not pInfo.plugin_object.is_activated:
                    print "Plugin is not loaded."
                else:
                    get_server().plugin_manager.deactivatePluginByName(pInfo.name,pInfo.categories[0])
                    self.parent.removeModule(pInfo.plugin_object)
            except:
                log_exception("while unloading plugin")
    
    def do_plugin(self, args):
        """
        Plugin management
        Usage: plugin list [<category>]                 - list the available plugins
               plugin load <plugin> [<plugin2> [...]]   - get an overview of the options in a category
               plugin unload <plugin> [<plugin2> [...]] - print the current value of an option
        """
        if len(args) == 0:
            return self.printHelp("plugin")
        args = shlex.split(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.listPlugins(args)
        elif subcmd == "load":
            self.loadPlugins(args)
        elif subcmd == "unload":
            self.unloadPlugins(args)
        else:
            return self.printHelp("plugin")
        pass
    
    def completeList(self, _args, _argNum, _text):
        return (aCat for aCat in get_server().plugin_manager.getCategories() if aCat.startswith(_text))
    
    def completePluginNames(self, _args, _argNum, text, listActivated, listDeactivated):
        text = text.lower()
        candidates = (name.lower().replace(" ", "\\ ") for name, _desc, _cats in self.getPluginNames(listActivated, listDeactivated))
        return (aValue for aValue in candidates if aValue.startswith(text))
    
    def complete_plugin(self, text, line, begidx, endidx):
        return self.completeSubcommands(text, line, begidx, endidx, {"list": self.completeList,
                                                                 "load": partial(self.completePluginNames, listActivated=False, listDeactivated=True),
                                                                 "unload": partial(self.completePluginNames, listActivated=True, listDeactivated=False)})
    