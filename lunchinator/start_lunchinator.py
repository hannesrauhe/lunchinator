#!/usr/bin/python
#
#this script is used to start the lunchinator in all its flavors

import platform, sys, os, logging, signal
from functools import partial
from optparse import OptionParser
from lunchinator import get_settings, get_server, set_has_gui, \
                    lunchinator_has_gui, MAIN_CONFIG_DIR
from lunchinator.log import getCoreLogger, initializeLogger
from lunchinator.log.lunch_logger import setGlobalLoggingLevel
from lunchinator.lunch_server import EXIT_CODE_STOP, EXIT_CODE_NO_QT
from lunchinator.utilities import INSTALL_CANCEL, INSTALL_SUCCESS, INSTALL_FAIL, \
    installDependencies, checkRequirements, handleMissingDependencies,\
    getPlatform, PLATFORM_MAC, isPyinstallerBuild
    

def parse_args():
    usage = "usage: %prog [options]"
    optionParser = OptionParser(usage = usage)
    optionParser.add_option("--install-dependencies",
                      default = False, dest = "installDep", action = "store_true",
                      help = "Trigger dependency installation")
    optionParser.add_option("--no-plugins",
                      default = False, dest = "noPlugins", action = "store_true",
                      help = "Disable plugins completely.")
    optionParser.add_option("--no-gui",
                      default = False, dest = "noGui", action = "store_true",
                      help = "Start Lunchinator without the GUI.")
    optionParser.add_option("--show-window",
                      default = False, dest = "showWindow", action = "store_true",
                      help = "Automatically open Lunchinator window.")
    optionParser.add_option("--cli",
                      default = False, dest = "cli", action = "store_true",
                      help = "Start Lunchinator with a command line interface.")
    optionParser.add_option("-s", "--send-message", default=None, dest="message",
                      help="Send a message to all members.")
    optionParser.add_option("-l", "--lunch-call", default=False, dest="lunchCall", action="store_true",
                      help="Send a lunch call to all members.")
    optionParser.add_option("-c", "--client", default=None, dest="client",
                      help="Send call to this specific member.")
    optionParser.add_option("--stop", default=False, dest="stop", action="store_true",
                      help="Stop local Lunch server.")
    optionParser.add_option("--no-broadcast", default=False, dest="noBroadcast", action="store_true",
                      help="Disable broadcasting if you are alone.")
    optionParser.add_option("--stopCode", default=False, dest="exitWithStopCode", action="store_true",
                      help="Exits immediately with the stop exit code.")
    optionParser.add_option("-v", "--verbose", default=False, dest="verbose", action="store_true",
                      help="Enable DEBUG output (override setting).")
    optionParser.add_option("-i", "--input", default=False, dest="input", action="store_true",
                      help="send input to clients")
    optionParser.add_option("-o", "--output", default=False, dest="output", action="store_true",
                      help="same as --no-gui --no-plugins - ideal for displaying piped content")
    optionParser.add_option("--version", default=False, dest="version", action="store_true",
                      help="Show Version and exit")
    return optionParser.parse_args()

def trace(frame, event, _):
    print "%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno)
    return trace
    
def sendMessage(msg, cli):
    if msg == None:
        msg = "lunch"
    
    get_settings().set_plugins_enabled(False)
    recv_nr=get_server().perform_call(msg,peerIDs=[],peerIPs=[cli])
    print "sent to",recv_nr,"clients"
    
def handleInterrupt(lanschi, _signal, _frame):
    lanschi.quit()    

def getCoreDependencies():
    try:
        req_file = get_settings().get_resource("requirements.txt")
        with open(req_file, 'r') as f:
            requirements = f.readlines()
    except IOError:
        getCoreLogger().warning("requirements.txt does not exist")
        requirements = []
    return requirements
        
def installCoreDependencies():  
    requirements = getCoreDependencies()
    missing = checkRequirements(requirements, u"Lunchinator", u"Lunchinator")
    result = handleMissingDependencies(missing, optionalCallback=lambda req : not "yapsy" in req.lower())
    if result == INSTALL_CANCEL:
        return False
    
    try:
        import yapsy
        if lunchinator_has_gui():
            from PyQt4.QtGui import QMessageBox
            if result == INSTALL_SUCCESS:
                QMessageBox.information(None,
                                        "Success",
                                        "Dependencies were installed successfully.",
                                        buttons=QMessageBox.Ok,
                                        defaultButton=QMessageBox.Ok)
            elif result == INSTALL_FAIL:
                QMessageBox.warning(None,
                                    "Errors during installation",
                                    "There were errors during installation, but Lunchinator might work anyways. If you experience problems with some plugins, try to install the required libraries manually using pip.")
            return True
        getCoreLogger().info("yapsy is working after dependency installation")
        #without gui there are enough messages on the screen already
    except:
        if lunchinator_has_gui():
            try:
                from PyQt4.QtGui import QMessageBox
                QMessageBox.critical(None,
                                     "Error installing dependencies",
                                     "There was an error, the dependencies could not be installed. Continuing without plugins.")
            except:
                getCoreLogger().error("There was an error, the dependencies could not be installed. Continuing without plugins.")
        getCoreLogger().error("Lunchinator is running without plugins because of missing dependencies. \
                Try executing 'lunchinator --install-dependencies' to install them automatically.")
        return False
        

def checkDependencies(noPlugins):
    """ Returns whether or not to use plugins, tries to install dependencies"""
    if noPlugins:
        return False
    
    try:
        import yapsy
        return True
    except:
        pass
    
    return installCoreDependencies()

def initLogger(options, path=None):
    initializeLogger(path)
    if options.verbose:
        get_settings().set_verbose(True)
        setGlobalLoggingLevel(logging.DEBUG)

def startLunchinator():
    (options, _args) = parse_args()
    usePlugins = options.noPlugins
    if options.output:      
        options.cli = False  
        options.nogui = True
        usePlugins = False
        
    defaultLogPath = os.path.join(MAIN_CONFIG_DIR, "lunchinator.log")
    if options.exitWithStopCode:
        sys.exit(EXIT_CODE_STOP)        
    elif options.version:
        initLogger(options)
        print "Lunchinator",get_settings().get_version()
        sys.exit(0)
    elif options.lunchCall or options.message != None:
        initLogger(options)
        get_settings().set_plugins_enabled(False)
        sendMessage(options.message, options.client)
    elif options.input:
        initLogger(options)
        get_settings().set_plugins_enabled(False)
        msg = sys.stdin.read()
        #@todo options.client
        if msg:
            sendMessage("HELO_LOCAL_PIPE "+msg, "127.0.0.1")
    elif options.stop:
        initLogger(options)
        get_settings().set_plugins_enabled(False)
        get_server().stop_server(stop_any=True)
        print "Sent stop command to local lunchinator"
    elif options.installDep:
        initLogger(options)
        req = getCoreDependencies()
        installDependencies(req)
        
        
    #lunchinator starts in listening mode:
    
    
    elif options.cli:
        initLogger(options, defaultLogPath)
        usePlugins = checkDependencies(usePlugins)
            
        retCode = 1
        try:
            from lunchinator import lunch_cli
            get_settings().set_plugins_enabled(usePlugins)
            get_server().set_disable_broadcast(options.noBroadcast)
            cli = lunch_cli.LunchCommandLineInterface()
            sys.retCode = cli.start()
        except:
            getCoreLogger().exception("cli version cannot be started, is readline installed?")
        finally:
            sys.exit(retCode)
    elif options.noGui:
        initLogger(options, defaultLogPath)
        usePlugins = checkDependencies(usePlugins)
        
    #    sys.settrace(trace)
        get_settings().set_plugins_enabled(usePlugins)
        get_server().set_disable_broadcast(options.noBroadcast)
        get_server().initialize()
        get_server().start_server()
        sys.exit(get_server().exitCode)
    else:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        try:
            initLogger(options, defaultLogPath)
        except os.error:
            if platform.system()=="Windows":
                #this usually means that the lunchinator is already started
                initLogger(options)
                sendMessage("HELO_OPEN_WINDOW please", "127.0.0.1")
                sys.exit(0)
            else:
                raise
                
        getCoreLogger().info("We are on %s, %s, version %s", platform.system(), platform.release(), platform.version())
        try:
            from PyQt4.QtCore import QThread            
            set_has_gui(True)
        except:
            getCoreLogger().error("pyQT4 not found - start lunchinator with --no-gui")
            sys.exit(EXIT_CODE_NO_QT)
            
        from lunchinator.gui_controller import LunchinatorGuiController
        from PyQt4.QtGui import QApplication
        
        class LunchApplication(QApplication):
            def notify(self, obj, event):
                try:
                    return QApplication.notify(self, obj, event)
                except:
                    getCoreLogger().exception("C++ Error")
                    return False
                        
        app = LunchApplication(sys.argv)
        usePlugins = checkDependencies(usePlugins)

        get_settings().set_plugins_enabled(usePlugins)
        get_server().set_disable_broadcast(options.noBroadcast)
        app.setQuitOnLastWindowClosed(False)
        lanschi = LunchinatorGuiController()
        if lanschi.isShuttingDown():
            # seems lanschi would prefer to not start up
            sys.exit(0)
        if options.showWindow:
            lanschi.openWindowClicked()
            
        if getPlatform() == PLATFORM_MAC and isPyinstallerBuild():
            import AppKit
            class MyDelegate(AppKit.AppKit.NSObject):
                def applicationShouldHandleReopen_hasVisibleWindows_(self, _app, hasOpenWindow):
                    if not hasOpenWindow:
                        lanschi.openWindowClicked()
            
            delegate = MyDelegate.alloc().init()
            AppKit.AppKit.NSApplication.sharedApplication().setDelegate_(delegate)
        
        # enable CRTL-C
        signal.signal(signal.SIGINT, partial(handleInterrupt, lanschi))
    
        try:
            app.exec_()
        finally:
            retValue = lanschi.quit()
            sys.exit(retValue)
    
