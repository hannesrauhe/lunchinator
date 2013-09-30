#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as GTK tray icon without self-updating functionality

import __preamble
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.gui_general import lunchinator
from lunchinator import get_settings, get_server
from lunchinator.lunch_settings import lunch_options_parser
from PyQt4.QtGui import QSystemTrayIcon, QIcon, QApplication
import sys,os,platform

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
    
if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
    
    lanschi = None
    mainWindow = None
    
    def serverInitialized():
        lanschi.serverInitialized()
        icon_file = get_settings().lunchdir+os.path.sep+"images"+os.path.sep+"qt.png"
        if platform.system()=="Windows":
            get_settings().lunchdir+os.path.sep+"images"+os.path.sep+"lunch.svg"
        icon = QIcon(icon_file)
        statusicon = QSystemTrayIcon(icon, mainWindow)
        contextMenu = lanschi.init_menu(mainWindow)
        statusicon.setContextMenu(contextMenu)
        statusicon.show()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    mainWindow = LunchinatorWindow()
    lanschi = lunchinator(mainWindow, options.noUpdates)
    lanschi.mainWindow = mainWindow
    mainWindow.guiHandler = lanschi
    
    lanschi.start()
    get_server().init_done.connect(serverInitialized)
    sys.exit(app.exec_())
