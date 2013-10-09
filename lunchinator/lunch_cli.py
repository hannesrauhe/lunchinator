import cmd, threading, time, shlex
from lunchinator import get_server, log_exception
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
        
    def complete_send(self, text, line, begidx, _endidx):
        args = shlex.split(line[:begidx])
        if len(args) > 1:
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
            # list settings in category
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
            
        po.set_option(option, args[2])
    
    def resetOption(self, args):
        pass
    
    def do_options(self, args):
        """Show or edit settings.
Usage: options list                                 - get an overview of the option categories
       options list <category>                      - get an overview of the options in a category
       options get <category> <setting>             - print the current value of an option
       options set <category> <setting> <new_value> - change the value of an option to a new value
       options reset <category> <setting>           - reset the value of an option.
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
       
    
    def do_exit(self, _):
        """Exits the application."""
        return True

    def do_EOF(self, _line):
        return True
