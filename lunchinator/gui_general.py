import sys,types
from lunchinator import get_server, log_exception, log_info, get_settings,\
    log_error
import time, socket,logging,os
import platform
import urllib2
import traceback    
from StringIO import StringIO   
from PyQt4.QtGui import QTabWidget, QMainWindow, QGridLayout, QLabel, QTextEdit, QLineEdit, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QApplication, QPushButton, QMessageBox, QSortFilterProxyModel
from PyQt4.QtCore import Qt, QThread, QTimer
from PyQt4 import QtCore
from functools import partial
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.lunch_settings_dialog import LunchinatorSettingsDialog
from lunchinator.table_models import MembersTableModel, MessagesTableModel
        
class lunchinator(QThread):
    _menu = None
    
    def __init__(self, parent, noUpdates = False): 
        super(lunchinator, self).__init__(parent)
        get_server().no_updates = noUpdates
        self.mainWindow = None
    
    def serverInitialized(self):
        messagesModel = MessagesTableModel(get_server())
        messagesProxyModel = QSortFilterProxyModel(get_server())
        messagesProxyModel.setDynamicSortFilter(True)
        messagesProxyModel.setSourceModel(messagesModel)
        self.mainWindow.messagesTable.setModel(messagesProxyModel)
        
        membersModel = MembersTableModel(get_server())
        membersProxyModel = QSortFilterProxyModel(get_server())
        membersProxyModel.setDynamicSortFilter(True)
        membersProxyModel.setSourceModel(membersModel)
        self.mainWindow.membersTable.setModel(membersProxyModel)
        timeoutTimer = QTimer(membersModel)
        timeoutTimer.setInterval(1000)
        timeoutTimer.timeout.connect(membersModel.updateTimeouts)
        timeoutTimer.start(1000)  
        
        self.mainWindow.serverInitialized()
        get_server().messagePrepended.connect(messagesModel.externalRowPrepended)
        
        get_server().memberAppended.connect(membersModel.externalRowAppended)
        get_server().memberAppended.connect(messagesModel.updateSenders)
        get_server().memberUpdated.connect(membersModel.externalRowUpdated)
        get_server().memberUpdated.connect(messagesModel.updateSenders)
        get_server().memberRemoved.connect(membersModel.externalRowRemoved)
        get_server().memberRemoved.connect(messagesModel.updateSenders)
        
    
    def run(self):
        get_server().start_server()
        
    def getPlugins(self, cats):
        allPlugins = {}
        for p_cat in cats:
            for info in get_server().plugin_manager.getPluginsOfCategory(p_cat):
                allPlugins[info.name] = (p_cat, info.plugin_object)
        return allPlugins
           
    
    def clicked_send_msg(self,w,*data):
        if len(data):
            get_server().call_all_members(data[0])
        else:
            get_server().call_all_members(unicode(w.text().toUtf8(), 'utf-8'))
            w.setText("")
        
    def clicked_add_host(self,w):
        hostn = str(w.text().toUtf8())
        try:
            ip = socket.gethostbyname(hostn.strip())
            get_server().append_member(ip, hostn)
            w.setText("")
        except:
            d = QMessageBox(QMessageBox.Critical, "Error adding host", "Cannot add host: Hostname unknown", QMessageBox.Ok, w)
            d.exec_()
            
    def init_menu(self, parent):        
        #create the plugin submenu
        menu = QMenu(parent)
        plugin_menu = QMenu("PlugIns", menu)
        
        allPlugins= self.getPlugins(['general','called','gui'])
        for pluginName in sorted(allPlugins.iterkeys()):
            anAction = plugin_menu.addAction(pluginName)
            anAction.setCheckable(True)
            anAction.setChecked(allPlugins[pluginName][1].is_activated)
            anAction.triggered.connect(partial(self.toggle_plugin, anAction, allPlugins[pluginName][0]))
        
        #main _menu
        anAction = menu.addAction('Call for lunch')
        anAction.triggered.connect(partial(self.clicked_send_msg, 'lunch'))
        
        anAction = menu.addAction('Show Lunchinator')
        anAction.triggered.connect(self.window_msg)
        
        anAction = menu.addAction('Settings')
        anAction.triggered.connect(self.window_settings)
        
        menu.addMenu(plugin_menu)
        
        anAction = menu.addAction('Exit')
        anAction.triggered.connect(self.quit)
            
        return menu
            
    def toggle_plugin(self,w,p_cat,new_state):
        p_name = str(w.text().toUtf8())
        if new_state:
            po = get_server().plugin_manager.activatePluginByName(p_name,p_cat)
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.addPluginWidget(po, p_name)
        else:
            get_server().plugin_manager.deactivatePluginByName(p_name,p_cat)  
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.removePluginWidget(p_name)
        get_settings().write_config_to_hd()
        
    def stop_server(self,_):        
        if self.isRunning():
            get_server().running = False
            self.wait()  
            log_info("server stopped") 
        else:
            log_info("server not running")
    
    def check_new_msgs(self):
        return get_server().new_msg
    
    def reset_new_msgs(self):
        get_server().new_msg=False
        
    def disable_auto_update(self):
        get_settings().auto_update=False
                  
    def quit(self,w):
        if self.mainWindow != None and self.mainWindow.isVisible():
            self.mainWindow.close()
        self.stop_server(w)
        os._exit(0)     
      

    def window_msg(self, _):    
        self.reset_new_msgs() 
        
        if self.mainWindow == None:
            log_error("mainWindow is not initialized")
            return
        self.mainWindow.show()
            
    def window_msgClosed(self, _, *__):
        # TODO needed?
        pass
            
    def window_settings(self,w):
        if self.mainWindow == None:
            log_error("mainWindow not specified")
            return
        
        self.reset_new_msgs()        
        
        settingsDialog = LunchinatorSettingsDialog(self.mainWindow)
        resp = settingsDialog.exec_()
        
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                if resp==LunchinatorSettingsDialog.RESULT_SAVE:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data()
                    except:
                        log_exception("was not able to save data for plugin %s" % pluginInfo.name)
                else:
                    pluginInfo.plugin_object.discard_options_widget_data()
        get_settings().write_config_to_hd()
            
        get_server().call("HELO_INFO "+get_server().build_info_string())        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    win = QMainWindow()
    central = QWidget(win)
    win.setCentralWidget(central)
    lay = QVBoxLayout(win.centralWidget())
    lay.addWidget(QLabel("asdf", win.centralWidget()))
    lay.addWidget(QLineEdit(win.centralWidget()))
    
    hlay = QHBoxLayout()
    hlay.addWidget(QLabel("1", win.centralWidget()))
    hlay.addWidget(QLabel("2", win.centralWidget()))
    
    lay.addLayout(hlay)
    
    win.centralWidget().setLayout(lay)
    
    win.show()
    
    sys.exit(app.exec_())
