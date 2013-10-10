import shlex
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
                    yield (pluginInfo.name, pluginInfo.description)
        except:
            log_exception("while collecting option categories")
            
    def listPlugins(self, args):
        try:
            category = None
            if len(args) > 0:
                category = args[0]
            for name, desc in sorted(self.getPluginNames(True, False, category), key=lambda aTuple : aTuple[0]):
                self.appendOutput(name, "(loaded)", desc)
            for name, desc in sorted(self.getPluginNames(False, True, category), key=lambda aTuple : aTuple[0]):
                self.appendOutput(name, "", desc)
            self.flushOutput()
        except:
            log_exception("while printing plugin names")
            
    def loadPlugin(self, args):
        try:
            pluginName = args.pop(0).upper()
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
            
    def unloadPlugin(self, args):
        try:
            pluginName = args[0].upper()
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
        Usage: plugin list [<category>] - list the available plugins
               plugin load <plugin>     - get an overview of the options in a category
               plugin unload <plugin>   - print the current value of an option
        """
        if len(args) == 0:
            return self.printHelp("plugin")
        args = shlex.split(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.listPlugins(args)
        elif subcmd == "load":
            self.loadPlugin(args)
        elif subcmd == "unload":
            self.unloadPlugin(args)
        else:
            return self.printHelp("plugin")
        pass
    
    def completeList(self, _args, _argNum, _text):
        return (aCat for aCat in get_server().plugin_manager.getCategories() if aCat.startswith(_text))
    
    def completePluginNames(self, _args, argNum, text, listActivated, listDeactivated):
        if argNum == 0:
            text = text.lower()
            candidates = (name.lower().replace(" ", "\\ ") for name, _desc in self.getPluginNames(listActivated, listDeactivated))
            return (aValue for aValue in candidates if aValue.startswith(text))
    
    def complete_plugin(self, text, line, begidx, endidx):
        argNum, text = self.getArgNum(text, line, begidx, endidx)
        
        result = None
        if argNum == 1:
            # subcommand
            return [aVal for aVal in ("list", "load", "unload") if aVal.startswith(text)]
        elif argNum >= 2:
            # argument to subcommand
            args = shlex.split(line)[1:]
            subcmd = args.pop(0)
            
            if subcmd == "list":
                result = self.completeList(args, argNum - 2, text)
            elif subcmd == "load":
                result = self.completePluginNames(args, argNum - 2, text, listActivated=False, listDeactivated=True)
            elif subcmd == "unload":
                result = self.completePluginNames(args, argNum - 2, text, listActivated=True, listDeactivated=False)

        numWordsToOmit = 0 if len(text.split()) == 0 else len(text.split()) - 1
        if result != None:
            return [" ".join(aValue.split()[numWordsToOmit:]) for aValue in result]
        return None
    