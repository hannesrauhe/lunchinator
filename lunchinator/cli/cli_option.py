import shlex
from lunchinator.cli import LunchCLIModule
from lunchinator import get_server, log_exception, convert_string

class CLIOptionHandling(LunchCLIModule):
    def getOptionCategories(self):
        categories=[]        
        try:
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    if pluginInfo.plugin_object.has_options():
                        categories.append((pluginInfo.name, pluginInfo.description))
        except:
            log_exception("while collecting option categories")
        return categories
            
    def getPluginObject(self, cat):
        cat = cat.upper()
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
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
            for cat, desc in sorted(self.getOptionCategories(), key=lambda aTuple : aTuple[0]):
                print "%s - %s" % (cat, desc)
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
                    print "%s (value: %s, default: %s)" % (name, value, default)
                else:
                    print "%s - %s (value: %s, default: %s)" % (name, desc, value, default)
    
    def getOption(self, args):
        if len(args) < 2:
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
        value = po.get_option(option)
        print value
    
    def setOption(self, args):
        if len(args) < 3:
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
            
        po.set_option(convert_string(option), convert_string(args[2]))
    
    def resetOption(self, args):
        if len(args) < 2:
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
            
        po.reset_option(option)
    
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
        args = shlex.split(args)
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
            return [aValue for aValue in candidates if aValue.startswith(text)]
       
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
                return [aValue for aValue in candidates if aValue.startswith(text)]
            return None
       
    def complete_option(self, text, line, begidx, endidx):
        argNum, text = self.getArgNum(text, line, begidx, endidx)
        
        result = None
        if argNum == 1:
            # subcommand
            return [aVal for aVal in ("list", "get", "set", "reset") if aVal.startswith(text)]
        elif argNum >= 2:
            # argument to subcommand
            args = shlex.split(line)[1:]
            subcmd = args.pop(0)
            
            if subcmd == "list":
                result = self.completeList(args, argNum - 2, text)
            elif subcmd == "get":
                result = self.completeGet(args, argNum - 2, text)
            elif subcmd == "set":
                result = self.completeGet(args, argNum - 2, text)
            elif subcmd == "reset":
                return []

        numWordsToOmit = 0 if len(text.split()) == 0 else len(text.split()) - 1
        if result != None:
            return [" ".join(aValue.split()[numWordsToOmit:]) for aValue in result]
        return None