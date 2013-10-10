import shlex, inspect, sys, re
from lunchinator import get_server, log_exception

class LunchCLIModule(object):
    MAX_COL_WIDTH = 60
    MAX_TOTAL_WIDTH = 100
    COL_DEL = "  "
    
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
        
    def cutString(self, string, maxLen):
        if maxLen >= len(string):
            return string
        
        # if string[maxLen + 1] is whitespace, it is OK
        index = string[:maxLen + 1].rfind(" ")
        if index == -1:
            return string[:maxLen]
        # include whitespace
        return string[:index + 1] 
        
    def flushOutput(self):
        columns = []
        for aRow in self.outputTable:
            if len(aRow) > len(columns):
                for _ in range(len(aRow) - len(columns)):
                    columns.append(0)
            for col, aValue in enumerate(aRow):
                columns[col] = min(self.MAX_COL_WIDTH, max((columns[col], len(self.convertToString(aValue)))))
        
        totalWidth = sum(columns) + len(columns) * len(self.COL_DEL)
        if totalWidth > self.MAX_TOTAL_WIDTH:
            ratio = float(self.MAX_TOTAL_WIDTH) / totalWidth
            newTotal = 0
            for i in range(len(columns) - 1):
                columns[i] = columns[i] * ratio
                newTotal += columns[i]
            # assign remainint width to last column
            columns[-1] = self.MAX_TOTAL_WIDTH - newTotal
        
        # last column does not need to be padded
        # TODO
        #columns[-1] = 0
        
        for aRow in self.outputTable:
            remaining = [len(aVal) for aVal in aRow]
            totalRemaining = sum(remaining)
            
            while totalRemaining > 0:
                # add new row until nothing remains
                rowWords = []
                for col, word in enumerate(aRow):
                    cutString = self.cutString(word[len(word) - remaining[col]:], columns[col])
                    remaining[col] -= len(cutString)
                    totalRemaining -= len(cutString)
                    if cutString.endswith(" "):
                        cutString = cutString[:-1]
                    rowWords.append(cutString.ljust(columns[col]))
                print self.COL_DEL.join(rowWords)
        
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
