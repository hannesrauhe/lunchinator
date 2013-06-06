import subprocess,platform

pythonex_wo_console = "python"

if platform.system()=="Windows":
    pythonex_wo_console = "pythonw"
    
print "We are on",platform.system(),platform.release(),platform.version()

try:
    import gtk
    try:
        #on ubuntu start the indicator
        import appindicator
        subprocess.Popen(["python","indicator_applet.py"])
    except ImportError, e:
        #start the tray icon on windows and other linxu flavors
        subprocess.Popen([pythonex_wo_console,"gui_tray.py"])        
except ImportError, e:
    #start the CLI-Version if gtk is not available
    subprocess.Popen(["python","nogui.py"])