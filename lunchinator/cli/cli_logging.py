from lunchinator.cli import LunchCLIModule
from lunchinator.log.logging_func import loggingFunc
from lunchinator.log.lunch_logger import getLoggerNames, getLoggingLevel,\
    getSpecificLoggingLevel, setLoggingLevel
from lunchinator import get_settings
import logging, itertools

class CLILoggingHandling(LunchCLIModule):
    def __iterLoggerNames(self):
        for aLoggerName in getLoggerNames():
            if aLoggerName.startswith(u"lunchinator."):
                yield aLoggerName, aLoggerName[12:]
            else:
                yield aLoggerName, aLoggerName
    
    def __handleLogger(self, args, numArgs, handler):
        if len(args) > numArgs:
            loggerNameLower = args[0].lower()
            loggerName = None
            for aLoggerName, dispName in self.__iterLoggerNames():
                if aLoggerName.lower() == loggerNameLower or dispName.lower() == loggerNameLower:
                    loggerName = aLoggerName
                    break
            if loggerName is None:
                print "Unknown logger:", args[0]
                return
            handler(loggerName, args[1:])
        else:
            handler(None, args)
           
    def __getLoggingLevelDescription(self, level):
        if level is None:
            return u"Default"
        if level is logging.DEBUG:
            return u"Debug"
        if level is logging.INFO:
            return u"Info"
        if level is logging.WARNING:
            return u"Warning"
        if level is logging.ERROR:
            return u"Error"
        if level is logging.CRITICAL:
            return u"Critical"
        return u"<Unknown>"
    
    def __getLoggingLevelFromText(self, text):
        text = text.lower()
        if text in (u"default", u"global", u"none"):
            return None
        if text == u"debug":
            return logging.DEBUG
        if text == u"info":
            return logging.INFO
        if text == u"warning":
            return logging.WARNING
        if text == u"error":
            return logging.ERROR
        if text == u"critical":
            return logging.CRITICAL
        raise ValueError()
           
    def __listLoggers(self): 
        self.appendOutput(u"Logger", u"Level")
        self.appendSeparator()
        for loggerName, dispName in sorted(self.__iterLoggerNames(), key=lambda aTup: aTup[1].lower()):
            self.appendOutput(dispName, self.__getLoggingLevelDescription(getSpecificLoggingLevel(loggerName)))
        self.flushOutput()
    
    def __setLevel(self, loggerName, args):
        if len(args) == 0:
            self.printHelp(u"logging")
            return
        try:
            level = self.__getLoggingLevelFromText(args[0])
        except ValueError:
            print "Invalid logging level:", args[0]
        
        if loggerName is None:
            if level is None:
                print "Invalid default logging level:", args[0]
                return
            
            if level == logging.DEBUG:
                get_settings().set_logging_level(u"DEBUG")
            elif level == logging.INFO:
                get_settings().set_logging_level(u"INFO")
            elif level == logging.WARNING:
                get_settings().set_logging_level(u"WARNING")
            elif level == logging.ERROR:
                get_settings().set_logging_level(u"ERROR")
            elif level == logging.CRITICAL:
                get_settings().set_logging_level(u"CRITICAL")
                
        else:
            setLoggingLevel(loggerName, level)
            
    def __getLevel(self, loggerName, _args):
        if loggerName:
            level = getSpecificLoggingLevel(loggerName)
        else:
            level = getLoggingLevel(None)
        if level is None:
            realLevel = getLoggingLevel(loggerName)
            print "%s (%s)" % (self.__getLoggingLevelDescription(level),
                               self.__getLoggingLevelDescription(realLevel))
        else:
            print self.__getLoggingLevelDescription(level)
    
    @loggingFunc
    def do_logging(self, args):
        """
        Show or edit the logging level of different loggers.
        Usage: logging list
                   get a list of available loggers
               logging get [<logger>]
                   get the logging level of a specific logger or the
                   default logging level if no logger is given
               logging set [<logger>] <level>
                   set the logging level of a specific logger or set the
                   default logging level if no logger is given
        """
        if len(args) == 0:
            return self.printHelp("logging")
        args = self.getArguments(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.__listLoggers()
        elif subcmd == "get":
            self.__handleLogger(args, 0, self.__getLevel)
        elif subcmd == "set":
            self.__handleLogger(args, 1, self.__setLevel)
        else:
            return self.printHelp("logging")

    def __completeLevels(self, text, noDefault=False):
        for level in (u"debug", u"info", u"warning", u"error", u"critical"):
            if level.startswith(text):
                yield level
        if not noDefault and u"default".startswith(text):
            yield u"default"
       
    def __completeLoggers(self, text):
        for loggerName, dispName in self.__iterLoggerNames():
            loggerName = loggerName.replace(u" ", u"\\ ")
            dispName = dispName.replace(u" ", u"\\ ")
            if loggerName.lower().startswith(text):
                yield loggerName
            elif dispName.lower().startswith(text):
                yield dispName
       
    def _handleGet(self, _args, argNum, text):
        text = text.lower()
        if argNum == 0:
            return self.__completeLoggers(text)
        
    def _handleSet(self, _args, argNum, text):
        text = text.lower()
        if argNum == 0:
            return itertools.chain(self.__completeLevels(text, noDefault=True), self.__completeLoggers(text))
        if argNum == 1:
            return self.__completeLevels(text)
       
    def __completeList(self, _args, _argNum, _text):
        return []
       
    def complete_logging(self, text, line, begidx, endidx):
        try:
            return self.completeSubcommands(text, line, begidx, endidx, {"list": self.__completeList,
                                                                         "get": self._handleGet,
                                                                         "set": self._handleSet})
        except:
            self.logger.exception("Error completing logging command")
    
