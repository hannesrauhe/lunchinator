#!/usr/bin/python
#
#this script is used to start the lunchinator in all its flavors

import platform, sys, subprocess
import signal
from functools import partial
from optparse import OptionParser
from lunchinator import log_info, log_error, get_settings,\
    get_server, log_exception, initialize_logger
from lunchinator.lunch_server import EXIT_CODE_UPDATE, EXIT_CODE_STOP, EXIT_CODE_NO_QT
from lunchinator.utilities import getPlatform, PLATFORM_WINDOWS, restart
    
def parse_args():
    usage = "usage: %prog [options]"
    optionParser = OptionParser(usage = usage)
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
    optionParser.add_option("--stopCode", default=False, dest="exitWithStopCode", action="store_true",
                      help="Exits immediately with the stop exit code.")
    return optionParser.parse_args()

def trace(frame, event, _):
    print "%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno)
    return trace
    
def sendMessage(msg, cli):
    if msg == None:
        msg = "lunch"
    
    get_server().set_plugins_enabled(False)
    recv_nr=get_server().perform_call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
def handleInterrupt(lanschi, _signal, _frame):
    lanschi.quit()

def checkDependencies(noPlugins, gui = False):
    """ Returns whether or not to use plugins """
    if noPlugins:
        return False
    
    try:
        import yapsy
        return True
    except:
        if getPlatform()==PLATFORM_WINDOWS:
            #not possible to install pip with admin rights on Windows (although get-pip.py looked promising)
            msg = "There are missing dependencies. Install pip and run python -m pip install -r requirements.txt"
            if gui:                
                from PyQt4.QtGui import QMessageBox
                QMessageBox.critical(None,
                                         "Error: missing dependencies",
                                         msg)
            log_error(msg)
            return False
        if gui:
            from PyQt4.QtGui import QMessageBox
            mbox = QMessageBox (QMessageBox.Question,
                                "Dependencies missing",
                                "Some dependencies are missing and can installed using pip. You can select 'None' and continue without plugins.",
                                QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No)
            mbox.button(QMessageBox.Yes).setText("Minimal")
            mbox.button(QMessageBox.YesToAll).setText("Complete (recommended)")
            mbox.button(QMessageBox.No).setText("None")
            mbox.setDefaultButton(QMessageBox.YesToAll)
            mbox.setEscapeButton(QMessageBox.No)
            res = mbox.exec_()
            
            if res == QMessageBox.No:
                return False
            elif res == QMessageBox.Yes:
                # install only Yapsy
                deps = ['yapsy']
            elif res == QMessageBox.YesToAll:
                deps = ['yapsy', 'requests', 'requests-oauthlib', 'oauthlib', 'python-twitter', 'python-gnupg']
            
            result = subprocess.call([get_settings().get_resource('bin', 'install-dependencies.sh')] + deps)
            
            if result == EXIT_CODE_UPDATE:
                # need to restart
                restart()
                return
            
            try:
                import yapsy
                if result == 0:
                    QMessageBox.information(None,
                                            "Success",
                                            "Dependencies were installed successfully.",
                                            buttons=QMessageBox.Ok,
                                            defaultButton=QMessageBox.Ok)
                else:
                    QMessageBox.warning(None,
                                        "Errors during installation",
                                        "There were errors during installation, but Lunchinator might work anyways. If you experience problems with some plugins, try to install the required libraries manually using pip.")
                return True
            except:
                QMessageBox.critical(None,
                                     "Error installing dependencies",
                                     "There was an error, the dependencies could not be installed. Continuing without plugins.")
                log_error("Dependencies could not be installed.")
            return False

def startLunchinator():
    initialize_logger()
    
    (options, _args) = parse_args()
    usePlugins = options.noPlugins
    if options.exitWithStopCode:
        sys.exit(EXIT_CODE_STOP)
    elif options.lunchCall or options.message != None:
        sendMessage(options.message, options.client)
    elif options.stop:
        msg = "local"
        get_server().set_plugins_enabled(False)
        get_server().call("HELO_STOP "+msg,client="127.0.0.1")
        print "Sent stop command to local lunchinator"
    elif options.cli:
        usePlugins = checkDependencies(usePlugins)
            
        retCode = 1
        try:
            from lunchinator import lunch_cli
            get_server().set_plugins_enabled(usePlugins)
            get_server().set_has_gui(False)
            cli = lunch_cli.LunchCommandLineInterface()
            sys.retCode = cli.start()
        except:
            log_exception("cli version cannot be started, is readline installed?")
        finally:
            sys.exit(retCode)
    elif options.noGui:
        usePlugins = checkDependencies(usePlugins)
        
    #    sys.settrace(trace)
        get_server().set_plugins_enabled(usePlugins)
        get_server().set_has_gui(False)
        get_server().start_server()
        sys.exit(get_server().exitCode)
    else:    
        log_info("We are on",platform.system(),platform.release(),platform.version())
        try:
            from PyQt4.QtCore import QThread
        except:
            log_error("pyQT4 not found - start lunchinator with --no-gui")
            sys.exit(EXIT_CODE_NO_QT)
            
        from lunchinator.gui_controller import LunchinatorGuiController
        from PyQt4.QtGui import QApplication
        
        app = QApplication(sys.argv)
        usePlugins = checkDependencies(usePlugins, gui=True)

        get_server().set_plugins_enabled(usePlugins)
        app.setQuitOnLastWindowClosed(False)
        lanschi = LunchinatorGuiController()
        if lanschi.isShuttingDown():
            # seems lanschi would prefer to not start up
            sys.exit(0)
        if options.showWindow:
            lanschi.openWindowClicked()
        
        # enable CRTL-C
        signal.signal(signal.SIGINT, partial(handleInterrupt, lanschi))
    
        try:
            app.exec_()
        finally:
            retValue = lanschi.quit()
            sys.exit(retValue)
    
