#!/usr/bin/python
import subprocess,platform,os
from lunch_default_config import *

pythonex_wo_console = "python"

if platform.system()=="Windows":
    pythonex_wo_console = "pythonw"
    
print "We are on",platform.system(),platform.release(),platform.version()

config_object = lunch_default_config()

subprocess.call(["git","stash"])
subprocess.call(["git","pull"])

fhandle = file(config_object.main_config_dir+"/update", 'a')
fhandle.close()

while os.path.exists(config_object.main_config_dir+"/update"):        
    os.remove(config_object.main_config_dir+"/update")
    try:
        import gtk
        try:
            #on ubuntu start the indicator
            import appindicator
            subprocess.call(["python","indicator_applet.py"])
        except ImportError, e:
            #start the tray icon on windows and other linxu flavors
            subprocess.call([pythonex_wo_console,"gui_tray.py"])        
    except ImportError, e:
        #start the CLI-Version if gtk is not available
        subprocess.call(["python","nogui.py"])
