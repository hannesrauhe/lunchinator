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
import threading
    
class TrayIcon(QMainWindow, threading.Thread):
    def __init__(self, app):
        super(TrayIcon, self).__init__()
        self.app = app
        
        (options, args) = lunch_options_parser().parse_args()
    
        gobject.threads_init()
        
        self.lanschi = lunchinator(options.noUpdates)
        self.lanschi.start()
        get_server().init_done.wait()
    
        #pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(sys.path[0]+"/images/glyphicons_053_alarm_black.png",25,25)
        
        icon = QIcon("/Users/Corny/Documents/Python/Lunchinator/images/glyphicons_053_alarm_black.png")
        self.statusicon = QSystemTrayIcon(icon, self)
        self.statusicon.setContextMenu(self.init_menu())
        self.statusicon.show()
    
    def reset_icon(self, c):
        self.lanschi.reset_new_msgs()
        self.statusicon.set_blinking(False)
        
    def show_menu(self, icon, button, time, menu):
        self.reset_icon(None)
        menu.show_all()
        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.statusicon)
    
    def run(self):
        self.app.exec_()
    
    def init_menu(self):        
        #create the plugin submenu
        menu = QMenu()
        plugin_menu = QMenu("PlugIns", menu)
        
        allPlugins= self.lanschi.getPlugins(['general','called','gui'])
        for pluginName in sorted(allPlugins.iterkeys()):
            anAction = plugin_menu.addAction(pluginName)
            anAction.setCheckable(True)
            anAction.setChecked(allPlugins[pluginName][1].is_activated)
            anAction.triggered.connect(partial(self.lanschi.toggle_plugin, allPlugins[pluginName][0]))
        
        #main _menu
        anAction = menu.addAction('Call for lunch')
        anAction.triggered.connect(partial(self.lanschi.clicked_send_msg, 'lunch'))
        
        anAction = menu.addAction('Show Lunchinator')
        anAction.triggered.connect(self.lanschi.window_msg)
        
        anAction = menu.addAction('Settings')
        anAction.triggered.connect(self.lanschi.window_settings)
        
        menu.addMenu(plugin_menu)
        
        anAction = menu.addAction('Exit')
        anAction.triggered.connect(self.lanschi.quit)
            
        return menu
    
    
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    TrayIcon(app).run()
    try:
        gtk.main()
    finally:
        get_server().stop_server(None)
        os._exit(0)
