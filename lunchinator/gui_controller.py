import sys
from lunchinator import get_server, log_exception, log_info, get_settings,\
    log_error, convert_string, log_warning, log_debug
import socket,os,time
import platform
from PyQt4.QtGui import QMainWindow, QLabel, QLineEdit, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QApplication, QMessageBox, QAction, QSystemTrayIcon, QIcon
from PyQt4.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QByteArray, QCoreApplication, Qt
from functools import partial
from lunchinator.lunch_datathread_qt import DataReceiverThread, DataSenderThread
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.lunch_settings_dialog import LunchinatorSettingsDialog
from lunchinator.utilities import processPluginCall

class LunchServerThread(QThread):
    def __init__(self, parent):
        super(LunchServerThread, self).__init__(parent)
    
    def run(self):
        get_server().start_server()
        
class LunchinatorGuiController(QObject, LunchServerController):
    _menu = None
    # ---- SIGNALS ----------------
    _initDone = pyqtSignal()
    memberAppendedSignal = pyqtSignal(unicode, dict)
    memberUpdatedSignal = pyqtSignal(unicode, dict)
    memberRemovedSignal = pyqtSignal(unicode)
    messagePrependedSignal = pyqtSignal(time.struct_time, list)
    _sendFile = pyqtSignal(unicode, QByteArray, int, bool)
    _receiveFile = pyqtSignal(unicode, int, unicode)
    _processEvent = pyqtSignal(unicode, unicode, unicode)
    _processMessage = pyqtSignal(unicode, unicode)
    _processLunchCall = pyqtSignal(unicode, unicode)
    # -----------------------------
    
    def __init__(self, noUpdates = False): 
        QThread.__init__(self)
        LunchServerController.__init__(self)
        
        self.serverThread = None
        get_server().no_updates = noUpdates
        get_server().initialize(self)
        
        self.pluginNameToMenuAction = {}
        
        # initialize main window
        self.mainWindow = LunchinatorWindow(self)
        self.setParent(self.mainWindow)
        
        # initialize tray icon
        icon_file = get_settings().get_lunchdir()+os.path.sep+"images"+os.path.sep+"lunch.svg"
        if platform.system()=="Windows":
            get_settings().get_lunchdir()+os.path.sep+"images"+os.path.sep+"lunch.svg"
        icon = QIcon(icon_file)
        statusicon = QSystemTrayIcon(icon, self.mainWindow)
        contextMenu = self.init_menu(self.mainWindow)
        statusicon.setContextMenu(contextMenu)
        statusicon.show()
        
        # connect private signals
        self._initDone.connect(self.initDoneSlot)
        self._receiveFile.connect(self.receiveFileSlot)
        self._sendFile.connect(self.sendFileSlot)
        
        self._processEvent.connect(self.processEventSlot)
        self._processMessage.connect(self.processMessageSlot)
        self._processLunchCall.connect(self.processLunchCallSlot)
        self.running = True
        
        self.serverThread = LunchServerThread(self)
        self.serverThread.start()
        
    def getPlugins(self, cats):
        allPlugins = {}
        for p_cat in cats:
            for info in get_server().plugin_manager.getPluginsOfCategory(p_cat):
                allPlugins[info.name] = (p_cat, info.plugin_object)
        return allPlugins
    
    def quit(self):
        
        if self.mainWindow != None:
            self.mainWindow.close()
        if self.serverThread.isRunning():
            get_server().running = False
            log_info("Waiting maximal 30s for server to stop...")
            # wait maximal 30s 
            if self.serverThread.wait(30000):
                log_info("server stopped")
            else:
                log_warning("server not stopped properly")
        else:
            log_info("server not running")
             
        if self.running:
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.deactivate()
            log_info("plug-ins deactivated, exiting")
            self.running = False
        QCoreApplication.exit(get_server().exitCode)
        return get_server().exitCode
            
    """ ---------------- CALLED FROM LUNCH SERVER -----------------"""
    
    def initDone(self):
        self._initDone.emit()
        
    def serverStopped(self, exitCode):
        # emitted signal won't be processed anyway (plug-ins deactivated in quit())
        pass
        
    def memberAppended(self, ip, infoDict):
        self.memberAppendedSignal.emit(ip, infoDict)
    
    def memberUpdated(self, ip, infoDict):
        self.memberUpdatedSignal.emit(ip, infoDict)
    
    def memberRemoved(self, ip):
        self.memberRemovedSignal.emit(ip)
    
    def messagePrepended(self, messageTime, senderIP, messageText):
        self.messagePrependedSignal.emit(messageTime, [senderIP, messageText])
    
    def receiveFile(self, ip, fileSize, fileName):
        self._receiveFile.emit(ip, fileSize, fileName)
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData = False):
        if not isData:
            # encode to send as str
            fileOrData = fileOrData.encode('utf-8')
        self._sendFile.emit(ip, QByteArray.fromRawData(fileOrData), otherTCPPort, isData)

    """ process any non-message event """    
    def processEvent(self, cmd, hostName, senderIP):
        self._processEvent.emit(cmd, hostName, senderIP)
    
    """ process any message event, including lunch calls """
    def processMessage(self, msg, addr):
        self._processMessage.emit(msg, addr)
                    
    """ process a lunch call """
    def processLunchCall(self, msg, addr):
        self._processLunchCall.emit(msg, addr)
        
    """ ----------------- CALLED ON MAIN THREAD -------------------"""
    
    def init_menu(self, parent):        
        #create the plugin submenu
        menu = QMenu(parent)
        plugin_menu = QMenu("PlugIns", menu)
        
        allPlugins= self.getPlugins([u'general',u'called',u'gui',u'db'])
        for pluginName in sorted(allPlugins.iterkeys()):
            anAction = plugin_menu.addAction(pluginName)
            anAction.setCheckable(True)
            anAction.setChecked(allPlugins[pluginName][1].is_activated)
            anAction.toggled.connect(partial(self.toggle_plugin, anAction, allPlugins[pluginName][0]))
            self.pluginNameToMenuAction[pluginName] = anAction
        
        #main _menu
        anAction = menu.addAction('Call for lunch')
        anAction.triggered.connect(partial(self.sendMessageClicked, 'lunch', None))
        
        anAction = menu.addAction('Show Lunchinator')
        anAction.triggered.connect(self.openWindowClicked)
        
        anAction = menu.addAction('Settings')
        anAction.triggered.connect(self.openSettingsClicked)
        
        menu.addMenu(plugin_menu)
        
        anAction = menu.addAction('Exit')
        anAction.triggered.connect(self.quitClicked)
            
        return menu
    
    def check_new_msgs(self):
        return get_server().new_msg
    
    def reset_new_msgs(self):
        get_server().new_msg=False
        
    def disable_auto_update(self):
        get_settings().set_auto_update_enabled(False)
                  
                  
    """---------------------- SLOTS ------------------------------"""
    
    @pyqtSlot()
    def initDoneSlot(self):
        pass
    
    @pyqtSlot(unicode)
    def plugin_widget_closed(self, p_name):
        # just un-check the menu item, this will cause a callback
        anAction = self.pluginNameToMenuAction[p_name]
        anAction.setChecked(False)

    @pyqtSlot(QAction, unicode, bool)
    def toggle_plugin(self,w,p_cat,new_state):
        p_cat = convert_string(p_cat)
        p_name = unicode(w.text().toUtf8(), 'utf-8')
        if new_state:
            log_debug("Activating plugin '%s' of type '%s'" % (p_name, p_cat))
            po = get_server().plugin_manager.activatePluginByName(p_name,p_cat)
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.addPluginWidget(po, p_name, makeVisible=True)
        else:
            log_debug("Deactivating plugin '%s' of type '%s'" % (p_name, p_cat))
            get_server().plugin_manager.deactivatePluginByName(p_name,p_cat)  
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.removePluginWidget(p_name)
        get_settings().write_config_to_hd()
    
    @pyqtSlot(unicode, QObject)
    def sendMessageClicked(self, message, w):
        if message != None:
            message = convert_string(message)
            get_server().call_all_members(message)
        else:
            get_server().call_all_members(unicode(w.text().toUtf8(), 'utf-8'))
            w.setText("")
        
    @pyqtSlot(QLineEdit)
    def addHostClicked(self, w):
        hostn = unicode(w.text().toUtf8(), 'utf-8')
        try:
            ip = socket.gethostbyname(hostn.strip())
            get_server()._append_member(ip, hostn)
            w.setText("")
        except:
            d = QMessageBox(QMessageBox.Critical, "Error adding host", "Cannot add host: Hostname unknown", QMessageBox.Ok, w)
            d.exec_()
            
    @pyqtSlot(bool)
    def quitClicked(self,_):
        self.quit()

    @pyqtSlot(bool)
    def openWindowClicked(self, _):    
        self.reset_new_msgs() 
        
        if self.mainWindow == None:
            log_error("mainWindow is not initialized")
            return
        self.mainWindow.show()
            
    @pyqtSlot(bool)
    def openSettingsClicked(self,_):
        if self.mainWindow == None:
            log_error("mainWindow not specified")
            return
        
        self.reset_new_msgs()        
        
        settingsDialog = LunchinatorSettingsDialog(self.mainWindow)
        resp = settingsDialog.exec_()
        
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                if resp==LunchinatorSettingsDialog.Accepted:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data()
                    except:
                        log_exception("was not able to save data for plugin %s" % pluginInfo.name)
                else:
                    pluginInfo.plugin_object.discard_options_widget_data()
        get_settings().write_config_to_hd()
            
        get_server().call("HELO_INFO "+get_server()._build_info_string())        

    @pyqtSlot(QThread, unicode)
    def threadFinished(self, thread, _):
        thread.deleteLater()
        
    @pyqtSlot(unicode, QByteArray, int, bool)
    def sendFileSlot(self, addr, fileToSend, other_tcp_port, isData):
        addr = convert_string(addr)
        if isData:
            fileToSend = str(fileToSend)
        else:
            fileToSend = str(fileToSend).decode("utf-8")
        ds = DataSenderThread(self,addr,fileToSend, other_tcp_port, isData)
        ds.successfullyTransferred.connect(self.threadFinished)
        ds.errorOnTransfer.connect(self.threadFinished)
        ds.start()
    
    @pyqtSlot(unicode, int, unicode)
    def receiveFileSlot(self, addr, file_size, file_name):
        addr = convert_string(addr)
        file_name = convert_string(file_name)
        dr = DataReceiverThread(self,addr,file_size,file_name,get_settings().get_tcp_port())
        dr.successfullyTransferred.connect(self.threadFinished)
        dr.errorOnTransfer.connect(self.threadFinished)
        dr.start()
        
    @pyqtSlot(unicode, unicode, unicode)
    def processEventSlot(self, cmd, value, addr):
        cmd = convert_string(cmd)
        value = convert_string(value)
        addr = convert_string(addr)
        processPluginCall(addr, lambda p, ip, member_info: p.process_event(cmd, value, ip, member_info))
     
    @pyqtSlot(unicode, unicode)
    def processMessageSlot(self, msg, addr):
        msg = convert_string(msg)
        addr = convert_string(addr)
        processPluginCall(addr, lambda p, ip, member_info: p.process_message(msg, ip, member_info))
                    
    @pyqtSlot(unicode, unicode)
    def processLunchCallSlot(self, msg, addr):
        msg = convert_string(msg)
        addr = convert_string(addr)
        processPluginCall(addr, lambda p, ip, member_info: p.process_lunch_call(msg, ip, member_info))

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
