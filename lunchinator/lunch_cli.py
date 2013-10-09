import cmd, threading, time, shlex
from lunchinator import get_server
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
    
    def do_exit(self, _):
        """Exits the application."""
        return True

    def do_EOF(self, _line):
        return True
