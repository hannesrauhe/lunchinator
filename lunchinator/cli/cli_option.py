import sys
from lunchinator.cli import LunchCLIModule
from lunchinator import get_settings, get_plugin_manager, convert_string
from lunchinator.log import getLogger

class CLIOptionHandling(LunchCLIModule):
    def getOptionCategories(self):
        try:
            if get_settings().get_plugins_enabled():
                for pluginInfo in get_plugin_manager().getAllPlugins():
                    if pluginInfo.plugin_object.is_activated:
                        if pluginInfo.plugin_object.has_options():
                            yield (pluginInfo.name, pluginInfo.description)
        except:
            getLogger().exception("while collecting option categories")
            
    def getPluginObject(self, cat):
        cat = cat.upper()
        if get_settings().get_plugins_enabled():
            for pluginInfo in get_plugin_manager().getAllPlugins():
                if pluginInfo.plugin_object.is_activated and pluginInfo.name.upper() == cat:
                    return pluginInfo.plugin_object
        return None
            
    def getOptionsOfCategory(self, cat):
        po = self.getPluginObject(cat)
        if po != None:
            return ((aTuple[0], aTuple[1], po.get_option(aTuple[0]), po.get_option_default_value(aTuple[0])) for aTuple in po.get_option_names())
        return None
    
    def listOptions(self, args):
        if len(args) == 0:
            for name, desc in sorted(self.getOptionCategories(), key=lambda aTuple : aTuple[0]):
                self.appendOutput(name, desc)
            self.flushOutput()
        else:
            # list options in category
            category = args[0]
            optionNames = self.getOptionsOfCategory(category)
            if optionNames == None:
                print "Unknown category. The available categories are:"
                self.listOptions([])
                return
            
            for name, desc, value, default in optionNames:
                if desc == name:
                    desc = ""
                self.appendOutput(name, desc, "value: %s, default: %s" % (value, default))
            self.flushOutput()
    
    def handleOption(self, args, handler, numArgs = 0):
        if len(args) < 2 + numArgs:
            return self.printHelp("option")
        category = args[0]
        po = self.getPluginObject(category)
        if po == None:
            print "Unknown category. The available categories are:"
            self.listOptions([])
            return
        
        option = args[1].lower()
        if not po.has_option(option):
            print "Unknown option. The available options for category %s are:" % category
            self.listOptions([category])
            
        if numArgs > 0:
            handler(po, option, *args[2:])
        else:
            handler(po, option)
    
    def getOption(self, args):
        self.handleOption(args, lambda po, option: sys.stdout.write("%s\n" % po.get_option(option)))
    
    def setOption(self, args):
        self.handleOption(args, lambda po, option, new_v: po.set_option(convert_string(option), convert_string(new_v)), 1)
    
    def resetOption(self, args):
        self.handleOption(args, lambda po, option: po.reset_option(option))
    
    def do_option(self, args):
        """
        Show or edit options.
        Usage: option list                                - get an overview of the option categories
               option list <category>                     - get an overview of the options in a category
               option get <category> <option>             - print the current value of an option
               option set <category> <option> <new_value> - change the value of an option to a new value
               option reset <category> <option>           - reset the value of an option.
        """
        if len(args) == 0:
            return self.printHelp("option")
        args = self.getArguments(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.listOptions(args)
        elif subcmd == "get":
            self.getOption(args)
        elif subcmd == "set":
            self.setOption(args)
        elif subcmd == "reset":
            self.resetOption(args)
        else:
            return self.printHelp("option")
       
    def completeList(self, _args, argNum, text):
        if argNum == 0:
            text = text.lower()
            candidates = (aTuple[0].lower().replace(" ", "\\ ") for aTuple in self.getOptionCategories())
            return (aValue for aValue in candidates if aValue.startswith(text))
       
    def completeGet(self, args, argNum, text):
        if argNum == 0:
            # first argument is category
            return self.completeList(args, 0, text)
        elif argNum == 1:
            # second argument is option
            cat = args[0]
            candidates = self.getOptionsOfCategory(cat)
            if candidates != None:
                candidates = (aTuple[0].lower().replace(" ", "\\ ") for aTuple in self.getOptionsOfCategory(cat))
                return (aValue for aValue in candidates if aValue.startswith(text))
            return None
       
    def complete_option(self, text, line, begidx, endidx):
        return self.completeSubcommands(text, line, begidx, endidx, {"list": self.completeList,
                                                                     "get": self.completeGet,
                                                                     "set": self.completeGet,
                                                                     "reset": self.completeGet})
    