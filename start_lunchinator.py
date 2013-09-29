#!/usr/bin/python
import subprocess,platform,os,sys
from lunchinator.lunch_server import EXIT_CODE_UPDATE
from lunchinator import log_critical, log_error, log_info, get_settings,\
    log_warning

if os.path.exists("/opt/local/bin/python"):
    pythonex_wo_console = "/opt/local/bin/python"
else:
    pythonex_wo_console = "/usr/bin/python"

pythonex_w_console  = pythonex_wo_console

if platform.system()=="Windows":
    pythonex_w_console = "python"
    pythonex_wo_console = "pythonw"
    
log_info("We are on",platform.system(),platform.release(),platform.version())

lunchbindir = get_settings().lunchdir+"/bin/"

shouldRestart = True
while shouldRestart: 
    returnCode = 0
    
    if get_settings().auto_update:
        canUpdate, reason = get_settings().getCanUpdateMain()
        if not canUpdate:
            log_warning("Cannot update main repository: %s" % reason)
        else:
            log_info("Updating main repository")
            if get_settings().runGitCommand(["pull"]) != 0:
                log_error("git pull did not work (main repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the lunchinator directory %s start lunchinator again."%get_settings().lunchdir)
    
        if os.path.exists(get_settings().external_plugin_dir):    
            canUpdate, reason = get_settings().getCanUpdatePlugins()
            if not canUpdate:
                log_warning("Cannot update plugin repository: %s" % reason)
            else:
                log_info("Updating plugin repository")
                #locate plugins repository
                if get_settings().runGitCommand(["pull"], get_settings().external_plugin_dir) != 0:
                    log_error("git pull did not work (plugin repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the plugins directory %s/plugins and start lunchinator again."%get_settings().main_config_dir)
    shouldRestart = False       
    try:
        returnCode = subprocess.call([pythonex_wo_console,lunchbindir+"gui_tray.py","--autoUpdate"])        
    except ImportError, e:
        #start the CLI-Version if qt is not available
        returnCode = subprocess.call([pythonex_w_console,lunchbindir+"nogui.py"])
        
    if returnCode == EXIT_CODE_UPDATE:
        shouldRestart = True
