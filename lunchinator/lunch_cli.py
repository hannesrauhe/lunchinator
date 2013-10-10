import cmd, threading, time, inspect, new
from functools import partial
from lunchinator import get_server, log_error, get_settings, utilities
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.cli.cli_message import CLIMessageHandling
from lunchinator.cli.cli_option import CLIOptionHandling
from lunchinator.cli.cli_plugin import CLIPluginHandling

# enable tab completion on most platforms

if utilities.getPlatform() != utilities.PLATFORM_WINDOWS:
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

        self.commands = set(["exit"])
        self.addModule(CLIMessageHandling())  
        self.addModule(CLIOptionHandling())
        self.addModule(CLIPluginHandling(self))
        
        get_server().initialize(self)
        
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                self.addModule(pluginInfo.plugin_object)
                
        self.exitCode = 0
        self.initialized = False

    def initDone(self):
        self.initialized = True
        
    def printString(self, s):
        print s
        
    def addModule(self, cliModule):
        for name, value in inspect.getmembers(cliModule, inspect.ismethod):
            if name.startswith("do_"):
                cmdName = name[3:]
                if cmdName in self.commands:
                    log_error("Conflicting command name: 'do_%s' is defined multiple times")
                else:
                    self.commands.add(cmdName)
                    setattr(self.__class__, name, value)
                    docstring = inspect.getdoc(value)
                    if docstring:
                        setattr(self.__class__, "help_%s" % cmdName, partial(self.printString, docstring))
            elif name.startswith("complete_"):
                setattr(self.__class__, name, value)
    
    def removeModule(self, cliModule):
        for name, _value in inspect.getmembers(cliModule, inspect.ismethod):
            if name.startswith("do_"):
                cmdName = name[3:]
                if cmdName in self.commands:
                    self.commands.remove(cmdName)
                
                if hasattr(self.__class__, name):    
                    delattr(self.__class__, name)
                if hasattr(self.__class__, "help_%s" % cmdName):
                    delattr(self.__class__, "help_%s" % cmdName)
            elif name.startswith("complete_"):
                if hasattr(self.__class__, "complete_%s" % cmdName):
                    delattr(self.__class__, "complete_%s" % cmdName)

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
    
    def do_exit(self, _):
        """Exits the application."""
        return True

    def do_EOF(self, _line):
        return True
