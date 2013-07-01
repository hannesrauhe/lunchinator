#!/usr/bin/python
import subprocess,platform,os
from lunch_default_config import *
from lunch_server import EXIT_CODE_UPDATE

pythonex_wo_console = "python"

if platform.system()=="Windows":
    pythonex_wo_console = "pythonw"
    
print "We are on",platform.system(),platform.release(),platform.version()

config_object = lunch_default_config()

#subprocess.call(["git","stash"])
subprocess.call(["git","pull"])

shouldRestart = True
while shouldRestart: 
    shouldRestart = False       
    try:
        import gtk
        try:
            #on ubuntu start the indicator
            import appindicator
            returnCode = subprocess.call(["python","indicator_applet.py","--autoUpdate"])
            if returnCode == EXIT_CODE_UPDATE:
                shouldRestart = True
        except ImportError, e:
            #start the tray icon on windows and other linxu flavors
            subprocess.call([pythonex_wo_console,"gui_tray.py","--autoUpdate"])        
    except ImportError, e:
        #start the CLI-Version if gtk is not available
        subprocess.call(["python","nogui.py"])
