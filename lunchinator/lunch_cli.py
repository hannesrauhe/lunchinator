import sys, cmd, threading, time, shlex
from lunchinator import get_server, get_settings
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
    FRIENDS = [ 'Alice', 'Adam', 'Barbara', 'Bob' ]
    
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

    def do_call(self, args):
        """Call for lunch.
Usage: call [member1 [member2 [...]]]
        """
        args = shlex.split(args)
        
    def complete_call(self, text, _line, _begidx, _endidx):
        if text == None:
            text = ""
        get_server().lockMembers()
        lunchmembers = None
        try:
            lunchmemberNames = set([get_server().memberName(ip) for ip in get_server().get_members() if get_server().memberName(ip).startswith(text)])
            lunchMemberIPs = set([ip for ip in get_server().get_members() if ip.startswith(text)])
            lunchmembers = list(lunchmemberNames.union(lunchMemberIPs))
        finally:
            get_server().releaseMembers()
        return lunchmembers if lunchmembers != None else []
    
    def do_quit(self, _):
        """ Exits the application """
        return True
        
    def do_exit(self, _):
        """ Exits the application """
        return True

    def do_EOF(self, line):
        return True
