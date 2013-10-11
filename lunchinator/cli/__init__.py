import shlex, inspect, sys, re
from lunchinator import get_server, log_exception

class LunchCLIModule(object):
    MAX_COL_WIDTH = 60
    MAX_TOTAL_WIDTH = 100
    COL_DEL = "  "
    SEPARATOR = "="
    
    def __init__(self):
        super(LunchCLIModule, self).__init__()
        self.outputTable = []
    
    def _convertToString(self, value):
        if type(value) in (str, unicode):
            return value
        if type(value) == list:
            if len(value) == 1:
                return value[0]
            else:
                return ", ".join(value)
        return str(value)
    
    def appendOutput(self, *row):
        self.outputTable.append([self._convertToString(value) for value in row])
        
    def appendSeparator(self, sepChar = None):
        if sepChar == None:
            sepChar = self.SEPARATOR
        self.outputTable.append(str(sepChar))
        
    def _cutString(self, string, maxLen):
        if maxLen >= len(string):
            return string
        
        # if string[maxLen + 1] is whitespace, it is OK
        index = string[:maxLen + 1].rfind(" ")
        if index == -1:
            return string[:maxLen]
        # include whitespace
        return string[:index + 1] 
        
    def flushOutput(self, columnDelimiter = None, maxColumnWidth = None, maxTotalWidth = None):
        if columnDelimiter == None:
            columnDelimiter = self.COL_DEL
        if maxColumnWidth == None:
            maxColumnWidth = self.MAX_COL_WIDTH
        if maxTotalWidth == None:
            maxTotalWidth = self.MAX_TOTAL_WIDTH
        columns = []
        for aRow in self.outputTable:
            if type(aRow) == str:
                # separator
                continue
            if len(aRow) > len(columns):
                for _ in range(len(aRow) - len(columns)):
                    columns.append(0)
            for col, aValue in enumerate(aRow):
                columns[col] = min(maxColumnWidth, max((columns[col], len(aValue))))
        
        totalDelWidth = (len(columns) - 1) * len(columnDelimiter)
        totalWidth = sum(columns) + totalDelWidth
        if totalWidth > maxTotalWidth:
            # TODO implement good resizing algorithm
            pass
#             ratio = float(maxTotalWidth - totalDelWidth) / totalWidth
#             newTotal = 0
#             for i in range(len(columns) - 1):
#                 columns[i] = int(round(columns[i] * ratio))
#                 newTotal += columns[i]
#             # assign remaining width to last column
#             columns[-1] = maxTotalWidth - totalDelWidth - newTotal
#             totalWidth = maxTotalWidth
        
        for aRow in self.outputTable:
            if type(aRow) == str:
                # separator
                print aRow * (totalWidth / len(aRow))
                continue
            remaining = [len(aVal) for aVal in aRow]
            totalRemaining = sum(remaining)
            
            while totalRemaining > 0:
                # print new row until nothing remains
                rowWords = []
                for col, word in enumerate(aRow):
                    cutString = self._cutString(word[len(word) - remaining[col]:], columns[col])
                    remaining[col] -= len(cutString)
                    totalRemaining -= len(cutString)
                    if cutString.endswith(" "):
                        cutString = cutString[:-1]
                    if col == len(columns):
                        # last string does not need to be padded
                        rowWords.append(cutString)
                    else:
                        rowWords.append(cutString.ljust(columns[col]))
                print columnDelimiter.join(rowWords)
        
        self.outputTable = []
    
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
