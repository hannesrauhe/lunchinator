#!/usr/bin/python
import subprocess,platform,os,sys
from lunchinator.lunch_server import EXIT_CODE_UPDATE

pythonex_wo_console = "/usr/bin/python"
pythonex_w_console = "/usr/bin/python"

if platform.system()=="Windows":
    pythonex_w_console = "python"
    pythonex_wo_console = "pythonw"
    
print "We are on",platform.system(),platform.release(),platform.version()

lunchdir = sys.path[0]
lunchbindir = lunchdir+"/bin/"
main_config_dir = os.getenv("HOME")+"/.lunchinator" if os.getenv("HOME") else os.getenv("USERPROFILE")+"/.lunchinator"
main_confid_dir = os.path.abspath(main_config_dir)
print main_config_dir


shouldRestart = True
while shouldRestart: 
    returnCode = 0
    #subprocess.call(["git","--git-dir="+lunchdir+"/.git","stash"])
    if subprocess.call(["git","--git-dir="+lunchdir+"/.git","pull"])!=0:
        print "git pull did not work (main repository). The Update mechanism therefore does not work."
        print "If you do not know, what to do now:"
        print "it should be safe to call 'git stash' in the lunchinator directory %s start lunchinator again."%lunchdir
    
    #locate plugins repository
    if subprocess.call(["git","--git-dir="+main_config_dir+"/plugins/.git","pull"])!=0:
        print "git pull did not work (plugin repository). The Update mechanism therefore does not work."
        print "If you do not know, what to do now:"
        print "it should be safe to call 'git stash' in the plugins directory %s/plugins and start lunchinator again."%main_config_dir
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
