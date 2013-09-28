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
    
class TrayIcon(LunchinatorWindow):
    def __init__(self,lunchinator):
        super(TrayIcon, self).__init__(lunchinator)
    
        gobject.threads_init()
    
        icon = QIcon(sys.path[0]+"/images/qt.png")
        self.statusicon = QSystemTrayIcon(icon, self)
        self.statusicon.setContextMenu(lunchinator.init_menu())
        self.statusicon.show()
    
if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
    lanschi = lunchinator(options.noUpdates)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    lanschi.start()
    get_server().init_done.wait()
    
    mainWindow = TrayIcon(lanschi)
    lanschi.mainWindow = mainWindow
    
    try:
        sys.exit(app.exec_())
    finally:
        lanschi.stop_server(None)
        os._exit(0)
