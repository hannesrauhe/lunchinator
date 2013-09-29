#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as GTK tray icon without self-updating functionality

import __preamble
from lunchinator.gui_general import *
from lunchinator.lunch_settings import lunch_options_parser
from lunchinator import get_server
from PyQt4.QtGui import QMenu, QSystemTrayIcon, QApplication, QIcon, QMainWindow
from PyQt4 import QtCore
from functools import partial
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.gui_general import lunchinator
    
    
if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
    
    lanschi = None
    mainWindow = None
    def serverInitialized():
        lanschi.serverInitialized()
        icon = QIcon(get_settings().lunchdir+"/images/qt.png")
        statusicon = QSystemTrayIcon(icon, mainWindow)
        statusicon.setContextMenu(lanschi.init_menu())
        statusicon.show()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    mainWindow = LunchinatorWindow()
    lanschi = lunchinator(mainWindow, options.noUpdates)
    lanschi.mainWindow = mainWindow
    mainWindow.guiHandler = lanschi
    
    lanschi.start()
    get_server().init_done.connect(serverInitialized)
    
    retCode = 0
    try:
        retCode = app.exec_()
    finally:
        lanschi.stop_server(None)
        sys.exit(retCode)
    
