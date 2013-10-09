import shlex
from lunchinator.cli import LunchCLIModule
from lunchinator import get_server, log_exception

class CLIPluginHandling(LunchCLIModule):
    def __init__(self, parent):
        super(CLIPluginHandling, self).__init__()
        self.parent = parent
    
    def listPlugins(self, _args):
        try:
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                print "%s%s" % (pluginInfo.name, " (loaded)" if pluginInfo.plugin_object.is_activated else "")
        except:
            log_exception("while printing plugin names")
            
    def loadPlugin(self, args):
        try:
            pluginName = args[0].upper()
            po = None
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.name.upper() == pluginName:
                    po = pluginInfo.plugin_object
            if po == None:
                print "Unknown plugin. The available plugins are:"
                self.listPlugins(args)
            else:
                po.activate()
                self.parent.addModule(po)
        except:
            log_exception("while loading plugin")
            
    def unloadPlugin(self, args):
        try:
            pluginName = args[0].upper()
            po = None
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.name.upper() == pluginName:
                    po = pluginInfo.plugin_object
            if po == None:
                print "Unknown plugin. The available plugins are:"
                self.listPlugins(args)
            else:
                po.deactivate()
                self.parent.removeModule(po)
        except:
            log_exception("while unloading plugin")
    
    def do_plugin(self, args):
        """
        Plugin management
        Usage: plugin list            - list the available plugins
               plugin load <plugin>   - get an overview of the options in a category
               plugin unload <plugin> - print the current value of an option
        """
        if len(args) == 0:
            return self.do_help("plugin")
        args = shlex.split(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.listPlugins(args)
        elif subcmd == "load":
            self.loadPlugin(args)
        elif subcmd == "unload":
            self.unloadPlugin(args)
        else:
            return self.do_help("plugin")
        pass