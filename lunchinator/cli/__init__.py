import shlex, inspect, sys
from lunchinator import get_server, log_exception

class LunchCLIModule(object):
    def __init__(self):
        super(LunchCLIModule, self).__init__()
        self.outputTable = []
    
    def appendOutput(self, *row):
        self.outputTable.append(row)
        
    def convertToString(self, value):
        if type(value) in (str, unicode):
            return value
        return str(value)
        
    def printHelp(self, cmd):
        """ Emulate do_help from cmd.Cmd """
        if hasattr(self.__class__, "do_%s" % cmd):
            method = getattr(self.__class__, "do_%s" % cmd)
            doc = inspect.getdoc(method)
            if doc:
                print doc
            else:
                print "No help available for command %s" % cmd
        else:
            print "Unknown command: %s" % cmd
        
    def flushOutput(self):
        columns = []
        for aRow in self.outputTable:
            if len(aRow) > len(columns):
                for _ in range(len(aRow) - len(columns)):
                    columns.append(0)
            for col, aValue in enumerate(aRow):
                columns[col] = max((columns[col], len(self.convertToString(aValue))))
        
        # last column does not need to be padded
        columns[-1] = 0
        
        for aRow in self.outputTable:
            print "".join(word.ljust(columns[col] + 1) for col, word in enumerate(aRow))
        
        self.outputTable = []
    
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
    
    def completeHostnames(self, text):
        get_server().lockMembers()
        lunchmembers = None
        try:
            lunchmemberNames = set((get_server().memberName(ip) for ip in get_server().get_members() if get_server().memberName(ip).startswith(text)))
            lunchmembers = list(lunchmemberNames.union((ip for ip in get_server().get_members() if ip.startswith(text))))
        finally:
            get_server().releaseMembers()
        return lunchmembers if lunchmembers != None else []
    
    def getArgNum(self, text, line, _begidx, endidx):
        prevArgs = shlex.split(line[:endidx + 1])
        argNum = len(prevArgs)
        
        if len(text) > 0 or prevArgs[-1][-1] == ' ':
            # the current word is the completed word
            return (argNum - 1, prevArgs[-1].replace(" ", "\\ "))
        # complete an empty word
        return (argNum, "")
