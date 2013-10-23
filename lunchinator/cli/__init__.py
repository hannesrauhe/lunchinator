import shlex, inspect, sys, re
from lunchinator import get_server, log_exception, convert_string

class LunchCLIModule(object):
    MAX_COL_WIDTH = 60
    MAX_TOTAL_WIDTH = 100
    COL_DEL = "  "
    SEPARATOR = "="
    
    def __init__(self):
        super(LunchCLIModule, self).__init__()
        self.outputTable = []
    
    @classmethod
    def getArguments(cls, args):
        return [convert_string(anArg) for anArg in shlex.split(args)]
    
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
    
    def _getHostnames(self, _args, _argNum, prefix):
        get_server().lockMembers()
        lunchmembers = None
        try:
            lunchmemberNames = set((get_server().memberName(ip).replace(u" ", u"\\ ") for ip in get_server().get_members() if get_server().memberName(ip).replace(u" ", u"\\ ").startswith(prefix)))
            lunchmembers = list(lunchmemberNames.union((ip for ip in get_server().get_members() if ip.startswith(prefix))))
        finally:
            get_server().releaseMembers()
        return lunchmembers if lunchmembers != None else []
    
    def completeHostnames(self, text, line, begidx, endidx):
        return self.completeCommand(text, line, begidx, endidx, self._getHostnames)
    
    def getArgNum(self, text, line, _begidx, endidx):
        prevArgs = [convert_string(anArg) for anArg in shlex.split(line[:endidx + 1])]
        argNum = len(prevArgs)
        
        if len(text) > 0 or prevArgs[-1][-1] == u' ':
            # the current word is the completed word
            return (argNum - 1, prevArgs[-1].replace(u" ", u"\\ "))
        # complete an empty word
        return (argNum, u"")
    
    def completeCommand(self, text, line, begidx, endidx, completions):
        """
        Convenience method to complete a command without subcommands.
        The completions callbacks must return a list or generator of strings and take 3 arguments:
         - all arguments to the command
         - The index of the argument we are completing
         - The prefix to complete
        """
        argNum, text = self.getArgNum(text, line, begidx, endidx)
        args = self.getArguments(line)[1:]
        result = completions(args, argNum - 1, text)

        if result != None:
            splitText = text.split()
            numWordsToOmit = len(splitText)
            # check if last whitespace is escaped
            if len(splitText) > 0 and splitText[-1][-1] != '\\':
                numWordsToOmit = numWordsToOmit - 1
            return [" ".join(aValue.split()[numWordsToOmit:]) for aValue in result]
    
    def completeSubcommands(self, text, line, begidx, endidx, subcommands):
        """
        Convenience method to complete a command with subcommands.
        The subcommands argument should be a dictionary of {subcommand: callback} entries.
        The callbacks must return a list or generator of strings and take 3 arguments:
         - all arguments to the subcommand
         - The index of the argument we are completing
         - The prefix to complete
        """
        argNum, text = self.getArgNum(text, line, begidx, endidx)
        
        if argNum == 1:
            # subcommand
            return [aVal for aVal in subcommands.keys() if aVal.startswith(text)]
        elif argNum >= 2:
            result = None
            
            # argument to subcommand
            args = self.getArguments(line)[1:]
            subcmd = args.pop(0)
            
            if subcmd in subcommands:
                result = subcommands[subcmd](args, argNum - 2, text)

                if result != None:
                    splitText = text.split()
                    numWordsToOmit = len(splitText)
                    # check if last whitespace is escaped
                    if len(splitText) > 0 and splitText[-1][-1] != '\\':
                        numWordsToOmit = numWordsToOmit - 1
                    return [u" ".join(aValue.split()[numWordsToOmit:]) for aValue in result]
        return None
