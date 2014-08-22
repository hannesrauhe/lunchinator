import cmd, threading, time, inspect
from functools import partial
from lunchinator import get_server, utilities,\
    get_notification_center, get_settings, get_plugin_manager
from lunchinator.log import getLogger, loggingFunc
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.cli.cli_message import CLIMessageHandling
from lunchinator.cli.cli_option import CLIOptionHandling
from lunchinator.cli.cli_plugin import CLIPluginHandling
from lunchinator.lunch_server import EXIT_CODE_UPDATE

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
        try:
            get_server().start_server()
        except:
            getLogger().exception("Exception in Lunch Server")
            get_server().running = False
        
    def stop(self):
        get_server().stop_server()

class LunchCommandLineInterface(cmd.Cmd, LunchServerController):
    def __init__(self):
        cmd.Cmd.__init__(self)
        LunchServerController.__init__(self)

        self.prompt = "> "
        self.commands = set(["exit"])
        self.addModule(CLIMessageHandling())  
        self.addModule(CLIOptionHandling())
        self.addModule(CLIPluginHandling(self))
        
        get_server().initialize(self)
        
        if get_settings().get_plugins_enabled():
            for pluginInfo in get_plugin_manager().getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    self.addModule(pluginInfo.plugin_object)
                
        get_notification_center().connectApplicationUpdate(self.notifyUpdates)
                
        self.exitCode = 0
        # if serverStopped is called, we can determine if it was a regular exit.
        self.cleanExit = False
        self.initialized = False

    def initDone(self):
        self.initialized = True
        
    def printString(self, s):
        print s
        
    def emptyline(self):
        return False
        
    def addModule(self, cliModule):
        for name, value in inspect.getmembers(cliModule, inspect.ismethod):
            if name.startswith("do_"):
                cmdName = name[3:]
                if cmdName in self.commands:
                    getLogger().error("Conflicting command name: 'do_%s' is defined multiple times", cmdName)
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
                cmdName = name[9:]
                if hasattr(self.__class__, "complete_%s" % cmdName):
                    delattr(self.__class__, "complete_%s" % cmdName)

    def start(self):
        self.serverThread = ServerThread()
        self.serverThread.start()
        
        print "Waiting until the lunch server is started..."
        waited = 0
        while not self.initialized and waited < 5:
            time.sleep(0.5)
            waited = waited + 0.5
        if not self.initialized:
            print "Lunch server did not initialize."
            self.serverThread.stop()
        else:
            print "Lunch server started."
        
        try:
            self.cmdloop()
        finally:
            if self.initialized:
                print "Waiting until the lunch server is stopped..."
                self.serverThread.stop()
            return self.exitCode

    def cmdloop(self, intro=None):
        print
        if self.initialized:
            print "Welcome to the Lunchinator. Type 'help' for an overview of the available commands."
        else:
            print "Lunch Server not running. You can still use some commands like sending messages."
            
        while True:
            try:
                cmd.Cmd.cmdloop(self, intro=intro)
                break
            except KeyboardInterrupt:
                print "^C"
    
    @loggingFunc
    def notifyUpdates(self):
        print "There are updates available for you. Please exit to fetch the updates."
        self.prompt = "(update available)> "
    
    def serverStopped(self, exit_code):
        super(LunchCommandLineInterface, self).serverStopped(exit_code)
        if exit_code == EXIT_CODE_UPDATE:
            self.notifyUpdates()
        elif not self.cleanExit:
            print "Lunch server stopped. You can still use some commands like sending messages, but you have to restart for full functionality."
    
    def do_update(self, _):
        """Exits the application with the update exit code."""
        print "Shutting down for an update..."
        self.exitCode = EXIT_CODE_UPDATE
        return True
    
    def do_exit(self, _):
        """Exits the application."""
        self.cleanExit = True
        return True

    def do_EOF(self, _line):
        return True
