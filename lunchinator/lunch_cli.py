import cmd, threading, time, shlex
from lunchinator import get_server, log_exception, convert_string
from lunchinator.lunch_server_controller import LunchServerController

# enable tab completion on most platforms
import readline
import rlcompleter

if 'libedit' in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")

class ServerThread(threading.Thread):
    def run(self):
        get_server().start_server()
        
    def stop(self):
        get_server().running = False

class LunchCommandLineInterface(cmd.Cmd, LunchServerController):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.exitCode = 0
        self.initialized = False
        get_server().initialize(self)

    def initDone(self):
        self.initialized = True

    def start(self):
        self.serverThread = ServerThread()
        self.serverThread.start()
        print "Waiting until the lunch server is started..."
        while not self.initialized:
            time.sleep(1)
        print "Lunch server started."
        self.cmdloop()
        print "Waiting until the lunch server is stopped..."
        self.serverThread.stop()
        return self.exitCode

    def cmdloop(self, intro=None):
        print
        print "Welcome to the Lunchinator. Type 'help' for an overview of the available commands."
        while True:
            try:
                cmd.Cmd.cmdloop(self, intro=intro)
                break
            except KeyboardInterrupt:
                print "^C"

    def getHostList(self, args):
        hosts = []
        for member in args:
            if len(member) == 0:
                continue
            ip = get_server().ipForMemberName(member)
            if ip != None:
                hosts.append(ip)
            else:
                # assume IP or host name
                hosts.append(member)
        return hosts
        

    def do_send(self, args):
        """Send a message.
Usage: send <message>                             - Send message to all members
       send <message> <member1> [<member2> [...]] - Send message to specific members 
        """
        if len(args) == 0:
            self.do_help("send")
            return False
        args = shlex.split(args)
        message = args.pop(0)
        get_server().call(message, hosts=self.getHostList(args))
        
    def completeHostnames(self, text):
        get_server().lockMembers()
        lunchmembers = None
        try:
            lunchmemberNames = set([get_server().memberName(ip) for ip in get_server().get_members() if get_server().memberName(ip).startswith(text)])
            lunchMemberIPs = set([ip for ip in get_server().get_members() if ip.startswith(text)])
            lunchmembers = list(lunchmemberNames.union(lunchMemberIPs))
        finally:
            get_server().releaseMembers()
        return lunchmembers if lunchmembers != None else []
        
    def complete_send(self, text, line, begidx, endidx):
        if self.getArgNum(text, line, begidx, endidx)[0] > 1:
            # message is already entered, complete hostnames
            return self.completeHostnames(text)

    def do_call(self, args):
        """Call for lunch.
Usage: call                             - Call all members
       call <member1> [<member2> [...]] - Call specific members 
        """
        args = shlex.split(args)
        get_server().call("lunch", hosts=self.getHostList(args))
        
    def complete_call(self, text, _line, _begidx, _endidx):
        return self.completeHostnames(text)
    
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
        cat = cat.lower()
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated and pluginInfo.name.lower() == cat:
                return pluginInfo.plugin_object
        return None
            
    def getOptionsOfCategory(self, cat):
        po = self.getPluginObject(cat)
        if po != None:
            return po.get_option_names()
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
            
            for aTuple in optionNames:
                name = aTuple[0]
                desc = aTuple[1]
                if desc == name:
                    print name
                else:
                    print "%s - %s" % (name, desc)
    
    def getOption(self, args):
        if len(args) < 2:
            return self.do_help("options")
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
        print value, type(value) 
    
    def setOption(self, args):
        if len(args) < 3:
            return self.do_help("options")
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
        pass
    
    def do_options(self, args):
        """Show or edit options.
Usage: options list                                - get an overview of the option categories
       options list <category>                     - get an overview of the options in a category
       options get <category> <option>             - print the current value of an option
       options set <category> <option> <new_value> - change the value of an option to a new value
       options reset <category> <option>           - reset the value of an option.
       """
        if len(args) == 0:
            return self.do_help("options")
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
            return self.do_help("options")
       
    def completeList(self, _args, argNum, text):
        if argNum == 0:
            text = text.lower()
            candidates = [aTuple[0].lower().replace(" ", "\\ ") for aTuple in self.getOptionCategories()]
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
                candidates = [aTuple[0].lower().replace(" ", "\\ ") for aTuple in self.getOptionsOfCategory(cat)]
                return [aValue for aValue in candidates if aValue.startswith(text)]
            return None
       
    def getArgNum(self, text, line, _begidx, endidx):
        prevArgs = shlex.split(line[:endidx + 1])
        argNum = len(prevArgs)
        
        if len(text) > 0 or prevArgs[-1][-1] == ' ':
            # the current word is the completed word
            return (argNum - 1, prevArgs[-1].replace(" ", "\\ "))
        # complete an empty word
        return (argNum, "")
       
    def complete_options(self, text, line, begidx, endidx):
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
    
    def do_exit(self, _):
        """Exits the application."""
        return True

    def do_EOF(self, _line):
        return True