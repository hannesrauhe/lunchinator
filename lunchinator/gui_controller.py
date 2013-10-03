import sys
from lunchinator import get_server, log_exception, log_info, get_settings,\
    log_error
import socket,os,time
import platform
from PyQt4.QtGui import QMainWindow, QLabel, QLineEdit, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QApplication, QMessageBox, QSortFilterProxyModel, QAction, QSystemTrayIcon, QIcon
from PyQt4.QtCore import QThread, QTimer, pyqtSignal, pyqtSlot, QObject
from functools import partial
from lunchinator.lunch_datathread_qt import DataReceiverThread, DataSenderThread
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.lunch_settings_dialog import LunchinatorSettingsDialog
from lunchinator.table_models import MembersTableModel, MessagesTableModel

class LunchServerThread(QThread):
    def __init__(self, parent):
        super(LunchServerThread, self).__init__(parent)
    
    def run(self):
        get_server().start_server()
        
class LunchinatorGuiController(QObject, LunchServerController):
    _menu = None
    # ---- SIGNALS ----------------
    _initDone = pyqtSignal()
    _serverStopped = pyqtSignal()
    _memberAppended = pyqtSignal(unicode, dict)
    _memberUpdated = pyqtSignal(unicode, dict)
    _memberRemoved = pyqtSignal(unicode)
    _messagePrepended = pyqtSignal(time.struct_time, list)
    _sendFile = pyqtSignal(unicode, unicode, int)
    _receiveFile = pyqtSignal(unicode, int, unicode)
    _processEvent = pyqtSignal(unicode, unicode, unicode)
    # -----------------------------
    
    def __init__(self, noUpdates = False): 
        QThread.__init__(self)
        LunchServerController.__init__(self)
        
        self.serverThread = None
        get_server().no_updates = noUpdates
        get_server().initialize(self)
        
        # initialize main window
        self.mainWindow = LunchinatorWindow(self)
        self.setParent(self.mainWindow)
        
        # initialize messages table
        self.messagesModel = MessagesTableModel(get_server())
        self.messagesProxyModel = QSortFilterProxyModel(self)
        self.messagesProxyModel.setDynamicSortFilter(True)
        self.messagesProxyModel.setSourceModel(self.messagesModel)
        self.mainWindow.messagesTable.setModel(self.messagesProxyModel)
        self._messagePrepended.connect(self.messagesModel.externalRowPrepended)
        
        self._memberAppended.connect(self.updateSendersInMessagesTable)
        self._memberUpdated.connect(self.updateSendersInMessagesTable)
        self._memberRemoved.connect(self.updateSendersInMessagesTable)
        
        # initialize members table
        self.membersModel = MembersTableModel(get_server())
        self.membersProxyModel = QSortFilterProxyModel(self)
        self.membersProxyModel.setDynamicSortFilter(True)
        self.membersProxyModel.setSourceModel(self.membersModel)
        self.mainWindow.membersTable.setModel(self.membersProxyModel)
        timeoutTimer = QTimer(self.membersModel)
        timeoutTimer.setInterval(1000)
        timeoutTimer.timeout.connect(self.updateTimeoutsInMembersTables)
        timeoutTimer.start(1000)  
        
        self._memberAppended.connect(self.membersModel.externalRowAppended)
        self._memberUpdated.connect(self.membersModel.externalRowUpdated)
        self._memberRemoved.connect(self.membersModel.externalRowRemoved)
        
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
        self._serverStopped.connect(self.serverStoppedSlot)
        self._receiveFile.connect(self.receiveFileSlot)
        self._sendFile.connect(self.sendFileSlot)
        
        
        self.serverThread = LunchServerThread(self)
        self.serverThread.start()
        
    def getPlugins(self, cats):
        allPlugins = {}
        for p_cat in cats:
            for info in get_server().plugin_manager.getPluginsOfCategory(p_cat):
                allPlugins[info.name] = (p_cat, info.plugin_object)
        return allPlugins
      
    """ ---------------- CALLED FROM LUNCH SERVER -----------------"""
    
    def initDone(self):
        self._initDone.emit()
        
    def serverStopped(self):
        self._serverStopped.emit()
        
    def memberAppended(self, ip, infoDict):
        self._memberAppended.emit(ip, infoDict)
    
    def memberUpdated(self, ip, infoDict):
        self._memberUpdated.emit(ip, infoDict)
    
    def memberRemoved(self, ip):
        self._memberRemoved.emit(ip)
    
    def messagePrepended(self, messageTime, senderIP, messageText):
        self._messagePrepended.emit(messageTime, [senderIP, messageText])
    
    def receiveFile(self, ip, fileSize, fileName):
        self._receiveFile.emit(ip, fileSize, fileName)
    
    def sendFile(self, ip, filePath, otherTCPPort):
        self._sendFile.emit(ip, filePath, otherTCPPort)
    
    def processEvent(self, cmd, hostName, senderIP):
        self._processEvent.emit(cmd, hostName, senderIP)

        
    """ ----------------- CALLED ON MAIN THREAD -------------------"""
    
    def init_menu(self, parent):        
        #create the plugin submenu
        menu = QMenu(parent)
        plugin_menu = QMenu("PlugIns", menu)
        
        allPlugins= self.getPlugins(['general','called','gui','db'])
        for pluginName in sorted(allPlugins.iterkeys()):
            anAction = plugin_menu.addAction(pluginName)
            anAction.setCheckable(True)
            anAction.setChecked(allPlugins[pluginName][1].is_activated)
            anAction.triggered.connect(partial(self.toggle_plugin, anAction, allPlugins[pluginName][0]))
        
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
        
    def quit(self):
        if self.mainWindow != None:
            self.mainWindow.close()
        if self.serverThread.isRunning():
            get_server().running = False
        else:
            log_info("server not running")
    
    def check_new_msgs(self):
        return get_server().new_msg
    
    def reset_new_msgs(self):
        get_server().new_msg=False
        
    def disable_auto_update(self):
        get_settings().set_auto_update_enabled(False)
                  
                  
    """---------------------- SLOTS ------------------------------"""
    
    @pyqtSlot()
    def initDoneSlot(self):
        # TODO necessary?
        pass
    
    @pyqtSlot()
    def serverStoppedSlot(self):
        log_info("server stopped") 
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                pluginInfo.plugin_object.deactivate()
        log_info("plug-ins deactivated, exiting")
        # TODO quit with return code
        QApplication.quit()
        
    @pyqtSlot(QAction, unicode, bool)
    def toggle_plugin(self,w,p_cat,new_state):
        p_name = unicode(w.text().toUtf8(), 'utf-8')
        if new_state:
            po = get_server().plugin_manager.activatePluginByName(p_name,p_cat)
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.addPluginWidget(po, p_name)
        else:
            get_server().plugin_manager.deactivatePluginByName(p_name,p_cat)  
            if p_cat=="gui" and self.mainWindow != None:
                self.mainWindow.removePluginWidget(p_name)
        get_settings().write_config_to_hd()
    
    @pyqtSlot(unicode, QObject)
    def sendMessageClicked(self, message, w):
        if message != None:
            get_server().call_all_members(message)
        else:
            get_server().call_all_members(unicode(w.text().toUtf8(), 'utf-8'))
            w.setText("")
        
    @pyqtSlot(QLineEdit)
    def addHostClicked(self, w):
        hostn = unicode(w.text().toUtf8(), 'utf-8')
        try:
            ip = socket.gethostbyname(hostn.strip())
            get_server().append_member(ip, hostn)
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
                if resp==LunchinatorSettingsDialog.RESULT_SAVE:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data()
                    except:
                        log_exception("was not able to save data for plugin %s" % pluginInfo.name)
                else:
                    pluginInfo.plugin_object.discard_options_widget_data()
        get_settings().write_config_to_hd()
            
        get_server().call("HELO_INFO "+get_server().build_info_string())        

    @pyqtSlot(QThread, unicode)
    def threadFinished(self, thread, _):
        thread.deleteLater()
        
    @pyqtSlot(unicode, unicode, int)
    def sendFileSlot(self, addr, fileToSend, other_tcp_port):
        ds = DataSenderThread(self,addr,fileToSend, other_tcp_port)
        ds.successfullyTransferred.connect(self.threadFinished)
        ds.errorOnTransfer.connect(self.threadFinished)
        ds.start()
    
    @pyqtSlot(unicode, int, unicode)
    def receiveFileSlot(self, addr, file_size, file_name):
        dr = DataReceiverThread(self,addr,file_size,file_name,get_settings().get_tcp_port())
        dr.successfullyTransferred.connect(self.threadFinished)
        dr.errorOnTransfer.connect(self.threadFinished)
        dr.start()
        
    @pyqtSlot(unicode, unicode, unicode)
    def processEventSlot(self, cmd, value, addr):
        member_info = {}
        if get_server().member_info.has_key(addr):
            member_info = get_server().member_info[addr]
        for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("called")+get_server().plugin_manager.getPluginsOfCategory("gui"):
            if pluginInfo.plugin_object.is_activated:
                try:
                    pluginInfo.plugin_object.process_event(cmd,value,addr,member_info)
                except:
                    log_exception(u"plugin error in %s while processing event message" % pluginInfo.name)
     
    @pyqtSlot()
    def updateSendersInMessagesTable(self):
        self.messagesProxyModel.setDynamicSortFilter(False)
        self.messagesModel.updateSenders()
        self.messagesProxyModel.setDynamicSortFilter(True)
    
    @pyqtSlot()
    def updateTimeoutsInMembersTables(self):
        self.membersProxyModel.setDynamicSortFilter(False)
        self.membersModel.updateTimeouts()
        self.membersProxyModel.setDynamicSortFilter(True)

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
