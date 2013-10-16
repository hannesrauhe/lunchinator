#!/usr/bin/python
#
#this script is used to start the lunchinator in all its flavors

import platform, os, sys
import signal
from functools import partial
path = os.path.abspath(sys.argv[0])
while os.path.dirname(path) != path:
    if os.path.exists(os.path.join(path, 'lunchinator', '__init__.py')):
        sys.path.insert(0, path)
        break
    path = os.path.dirname(path)
    
from optparse import OptionParser
from lunchinator import log_info, log_warning, log_error, get_settings,\
    get_server, log_exception
from lunchinator.lunch_server import EXIT_CODE_UPDATE, EXIT_CODE_STOP, EXIT_CODE_NO_QT
    
def parse_args():
    usage = "usage: %prog [options]"
    optionParser = OptionParser(usage = usage)
    optionParser.add_option("--no-auto-update",
                      default = False, dest = "noUpdates", action = "store_true",
                      help = "Disable automatic updates from Git (override the GUI setting).")
    optionParser.add_option("--no-plugins",
                      default = False, dest = "noPlugins", action = "store_true",
                      help = "Disable plugins completely.")
    optionParser.add_option("--should-auto-update",
                      default = False, dest = "checkAutoUpdate", action = "store_true",
                      help = "Don't start Lunchinator but check if auto update is enabled. Exits with 1 if auto update is enabled.")
    optionParser.add_option("--update",
                      default = False, dest = "doUpdate", action = "store_true",
                      help = "Don't start Lunchinator but update the repository.")
    optionParser.add_option("--no-gui",
                      default = False, dest = "noGui", action = "store_true",
                      help = "Start Lunchinator without the GUI.")
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
    optionParser.add_option("--updateCode", default=False, dest="exitWithUpdateCode", action="store_true",
                      help="Exits immediately with the update exit code.")
    optionParser.add_option("--stopCode", default=False, dest="exitWithStopCode", action="store_true",
                      help="Exits immediately with the stop exit code.")
    return optionParser.parse_args()

def updateRepositories():
    # TODO check if lunch server is running, choose update mechanism accordingly
    running = False
    if not running:
        canUpdate, reason = get_settings().getCanUpdateMain()
        if not canUpdate:
            log_warning("Cannot update main repository: %s" % reason)
        else:
            log_info("Updating main repository")
            upd_res = get_settings().runGitCommand(["pull"])
            if upd_res[0] != 0:
                log_error("git pull did not work (main repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the lunchinator directory %s start lunchinator again.\n\
Error was: %s"%(get_settings().get_lunchdir(),str(upd_res)))

        if os.path.exists(get_settings().get_external_plugin_dir()):    
            canUpdate, reason = get_settings().getCanUpdatePlugins()
            if not canUpdate:
                log_warning("Cannot update plugin repository: %s" % reason)
            else:
                log_info("Updating plugin repository")
                #locate plugins repository
                upd_res = get_settings().runGitCommand(["pull"], get_settings().get_external_plugin_dir())
                if upd_res[0] != 0:
                    log_error("git pull did not work (plugin repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the plugins directory %s/plugins and start lunchinator again.\n\
Error was: %s"%(get_settings().get_main_config_dir(),str(upd_res)))
    else:
        msg = "local update"
        get_server().set_plugins_enabled(False)
        get_server().call("HELO_UPDATE "+msg,client="127.0.0.1")
        print "Sent update command to local lunchinator"

def trace(frame, event, _):
    print "%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno)
    return trace
    
def sendMessage(msg, cli):
    if msg == None:
        msg = "lunch"
    
    get_server().set_plugins_enabled(False)
    recv_nr=get_server().call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
def handleInterrupt(lanschi, _signal, _frame):
    lanschi.quit()
    
if __name__ == "__main__":
    (options, args) = parse_args()

    if options.exitWithUpdateCode:
        sys.exit(EXIT_CODE_UPDATE)
    elif options.exitWithStopCode:
        sys.exit(EXIT_CODE_STOP)
    elif options.doUpdate:
        # don't start Lunchinator, do update
        updateRepositories()
    elif options.checkAutoUpdate:
        if get_settings().get_auto_update_enabled():
            sys.exit(1)
        else:
            sys.exit(0)
    elif options.lunchCall or options.message != None:
        sendMessage(options.message, options.client)
    elif options.stop:
        msg = "local"
        get_server().set_plugins_enabled(False)
        recv_nr=get_server().call("HELO_STOP "+msg,client="127.0.0.1")
        print "Sent stop command to local lunchinator"
    elif options.cli:
        retCode = 1
        try:
            from lunchinator import lunch_cli
            get_server().no_updates = options.noUpdates
            get_server().set_plugins_enabled(not options.noPlugins)
            cli = lunch_cli.LunchCommandLineInterface()
            sys.retCode = cli.start()
        except:
            log_exception("cli version cannot be started, is readline installed")
        finally:
            sys.exit(retCode)
    elif options.noGui:
    #    sys.settrace(trace)
        get_server().no_updates = options.noUpdates
        get_server().set_plugins_enabled(not options.noPlugins)
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
        
        get_server().no_updates = options.noUpdates
        get_server().set_plugins_enabled(not options.noPlugins)
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        lanschi = LunchinatorGuiController(options.noUpdates)
        
        # enable CRTL-C
        signal.signal(signal.SIGINT, partial(handleInterrupt, lanschi))
    
        try:
            app.exec_()
        finally:
            retValue = lanschi.quit()
            sys.exit(retValue)
