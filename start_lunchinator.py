#!/usr/bin/python
import subprocess,platform,os,sys
from lunch_server import EXIT_CODE_UPDATE

pythonex_wo_console = "/usr/bin/python"
pythonex_w_console = "/usr/bin/python"

if platform.system()=="Windows":
    pythonex_w_console = "python"
    pythonex_wo_console = "pythonw"
    
print "We are on",platform.system(),platform.release(),platform.version()

os.chdir(sys.path[0])

shouldRestart = True
while shouldRestart: 
    returnCode = 0
    #subprocess.call(["git","stash"])
    if subprocess.call(["git","pull"])!=0:
        print "git pull did not work. The Update mechanism therefore does not work."
        print "If you do not know, what to do now:"
        print "it should be safe to call 'git stash' in the lunchinator directory and call 'python ./start_lunchinator.py' again."
    shouldRestart = False       
    try:
        import gtk
        try:
            #on ubuntu start the indicator
            import appindicator
            returnCode = subprocess.call([pythonex_wo_console,"indicator_applet.py","--autoUpdate"])
        except ImportError, e:
            #start the tray icon on windows and other linxu flavors
            returnCode = subprocess.call([pythonex_wo_console,"gui_tray.py","--autoUpdate"])        
    except ImportError, e:
        #start the CLI-Version if gtk is not available
        returnCode = subprocess.call([pythonex_w_console,"nogui.py"])
        
    if returnCode == EXIT_CODE_UPDATE:
        shouldRestart = True
