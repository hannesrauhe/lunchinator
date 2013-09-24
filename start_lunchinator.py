#!/usr/bin/python
import subprocess,platform,os,sys
from lunchinator.lunch_server import EXIT_CODE_UPDATE
from lunchinator import log_critical, log_error, log_info, get_settings,\
    log_warning

pythonex_wo_console = "/usr/bin/python"
pythonex_w_console = "/usr/bin/python"

if platform.system()=="Windows":
    pythonex_w_console = "python"
    pythonex_wo_console = "pythonw"
    
log_info("We are on",platform.system(),platform.release(),platform.version())

lunchbindir = get_settings().lunchdir+"/bin/"

shouldRestart = True
while shouldRestart: 
    returnCode = 0
    
    canUpdate, reason = get_settings().getCanUpdateMain()
    if not canUpdate:
        log_warning("Cannot update main repository: %s" % reason)
    else:
        log_info("Updating main repository")
        if subprocess.call(["git","--git-dir="+get_settings().lunchdir+"/.git","pull"])!=0:
            log_error("git pull did not work (main repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the lunchinator directory %s start lunchinator again."%get_settings().lunchdir)
    
    canUpdate, reason = get_settings().getCanUpdatePlugins()
    if not canUpdate:
        log_warning("Cannot update plugin repository: %s" % reason)
    else:
        log_info("Updating plugin repository")
        #locate plugins repository
        if subprocess.call(["git","--git-dir="+get_settings().main_config_dir+"/plugins/.git","pull"])!=0:
            log_error("git pull did not work (plugin repository). The Update mechanism therefore does not work.\n\
If you do not know, what to do now:\n\
it should be safe to call 'git stash' in the plugins directory %s/plugins and start lunchinator again."%get_settings().main_config_dir)
    shouldRestart = False       
    try:
        import gtk
        try:
            #on ubuntu start the indicator
            import appindicator
            returnCode = subprocess.call([pythonex_wo_console,lunchbindir+"indicator_applet.py","--autoUpdate"])
        except ImportError, e:
            #start the tray icon on windows and other linxu flavors
            returnCode = subprocess.call([pythonex_wo_console,lunchbindir+"gui_tray.py","--autoUpdate"])        
    except ImportError, e:
        #start the CLI-Version if gtk is not available
        returnCode = subprocess.call([pythonex_w_console,lunchbindir+"nogui.py"])
        
    if returnCode == EXIT_CODE_UPDATE:
        shouldRestart = True
