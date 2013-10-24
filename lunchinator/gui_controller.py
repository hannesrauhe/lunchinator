import sys, sip
from lunchinator import get_server, log_exception, log_info, get_settings,\
    log_error, convert_string, log_warning, log_debug
import socket,os,time, subprocess
import platform
from PyQt4.QtGui import QLineEdit, QMenu, QMessageBox, QAction, QSystemTrayIcon, QIcon, QCursor
from PyQt4.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QCoreApplication, QTimer
from PyQt4 import QtCore
from functools import partial
from lunchinator.lunch_datathread_qt import DataReceiverThread, DataSenderThread
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.lunch_settings_dialog import LunchinatorSettingsDialog
from lunchinator.utilities import processPluginCall, getPlatform, PLATFORM_MAC
from lunchinator.lunch_server import EXIT_CODE_UPDATE, EXIT_CODE_ERROR
from yapsy.PluginManager import PluginManagerSingleton

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
    groupAppendedSignal = pyqtSignal(unicode, set)
    _sendFile = pyqtSignal(unicode, bytearray, int, bool)
    _receiveFile = pyqtSignal(unicode, int, unicode, int)
    _processEvent = pyqtSignal(unicode, unicode, unicode)
    _processMessage = pyqtSignal(unicode, unicode)
    _processLunchCall = pyqtSignal(unicode, unicode)
    _updateRequested = pyqtSignal()
    # -----------------------------
    
    def __init__(self, noUpdates = False): 
        QObject.__init__(self)
        LunchServerController.__init__(self)
        
        log_info("Your PyQt version is %s, based on Qt %s" % (QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR))
        
        self.resetIconTimer = None
        self.isIconHighlighted = True # set to True s.t. first dehighlight can set the default icon
        
        self.exitCode = 0
        self.serverThread = None
        self.running = True
        get_server().no_updates = noUpdates
        get_server().initialize(self)
        
        self.pluginNameToMenuAction = {}
        
        # initialize main window
        self.mainWindow = LunchinatorWindow(self)
        self.setParent(self.mainWindow)
        
        if not self.createTrayIcon():
            return
        
        self.mainWindow.createMenuBar(self.pluginActions)
        
        # connect private signals
        self._initDone.connect(self.initDoneSlot)
        self._receiveFile.connect(self.receiveFileSlot)
        self._sendFile.connect(self.sendFileSlot)
        
        self._processEvent.connect(self.processEventSlot)
        self._processMessage.connect(self.processMessageSlot)
        self._processLunchCall.connect(self.processLunchCallSlot)
        self._updateRequested.connect(self.updateRequested)
        
        self.messagePrependedSignal.connect(self.highlightIcon)
        
        self.serverThread = LunchServerThread(self)
        self.serverThread.finished.connect(self.serverFinishedUnexpectedly)
        self.serverThread.finished.connect(self.serverThread.deleteLater)
        self.serverThread.start()
        
    def highlightIcon(self):
        if self.isIconHighlighted:
            return
        if self.mainWindow.isActiveWindow():
            # dont set highlighted if window is in foreground
            return
        self.isIconHighlighted = True
        icon_file = os.path.join(get_settings().get_lunchdir(), "images", "lunchred.svg")
        if hasattr(QIcon, "fromTheme"):
            icon = QIcon.fromTheme("lunchinatorred", QIcon(icon_file))
        else:
            icon = QIcon(icon_file)
        self.statusicon.setIcon(icon)
        
        if self.resetIconTimer == None:
            self.resetIconTimer = QTimer(self)
            self.resetIconTimer.setSingleShot(True)
            self.resetIconTimer.timeout.connect(self.dehighlightIcon)
        
        self.resetIconTimer.start(get_settings().get_reset_icon_time() * 60000)
        
    def dehighlightIcon(self):
        if not self.isIconHighlighted:
            return
        self.isIconHighlighted = False
        if self.resetIconTimer != None and self.resetIconTimer.isActive():
            self.resetIconTimer.stop()
        icon_file = os.path.join(get_settings().get_lunchdir(), "images", "lunch.svg")
        if hasattr(QIcon, "fromTheme"):
            icon = QIcon.fromTheme("lunchinator", QIcon(icon_file))
        else:
            icon = QIcon(icon_file)
        self.statusicon.setIcon(icon)
        
    def createTrayIcon(self):
        if platform.linux_distribution()[0] == "Ubuntu":
            if not os.path.exists('/usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg') or \
               not os.path.exists('/usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg'):
                result = QMessageBox.question(self.mainWindow,
                                              "Install Icons",
                                              "Do you want to install the Lunchinator icons into the Ubuntu theme folders? You will have to enter your sudo password.",
                                              buttons=QMessageBox.Yes | QMessageBox.No,
                                              defaultButton=QMessageBox.Yes)
                if result == QMessageBox.Yes:
                    if subprocess.call(['gksu', get_settings().get_lunchdir()+'/bin/install-lunch-icons.sh lunch'])==0:
                        log_info("restarting after icons were installed")
                        self.quit(EXIT_CODE_UPDATE)
                        sys.exit(EXIT_CODE_UPDATE)
                        return False
                    else:
                        QMessageBox.critical(self.mainWindow,
                                             "Error installing icons",
                                             "The icons were not installed, there was an error.",
                                             buttons=QMessageBox.Ok,
                                             defaultButton=QMessageBox.Ok)
                        log_info("icons were not installed because of an error")
        
        # initialize tray icon
        self.statusicon = QSystemTrayIcon(self.mainWindow)
        # dehighlightIcon sets the default icon
        self.dehighlightIcon()
        contextMenu = self.init_menu(self.mainWindow)
        self.statusicon.activated.connect(self.trayActivated)
        self.statusicon.setContextMenu(contextMenu)
        self.statusicon.show()
        return True
        
    def trayActivated(self, reason):
        if getPlatform() == PLATFORM_MAC:
            # Trigger is sent even though the context menu is shown.
            return
        if reason == QSystemTrayIcon.Trigger:
            self.statusicon.contextMenu().popup(QCursor.pos())
        
    def quit(self, exitCode = 0):
        if self.mainWindow != None:
            self.mainWindow.close()
        if self.serverThread != None and not sip.isdeleted(self.serverThread) and self.serverThread.isRunning():
            self.serverThread.finished.disconnect(self.serverFinishedUnexpectedly)
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
            
        finalExitCode = 0
        if exitCode != 0:
            finalExitCode = exitCode
        elif self.exitCode != 0:
            finalExitCode = self.exitCode
        else:
            finalExitCode = get_server().exitCode
            
        get_settings().write_config_to_hd()
            
        self.exitCode = finalExitCode
        QCoreApplication.exit(finalExitCode)
        return finalExitCode
            
    """ ---------------- CALLED FROM LUNCH SERVER -----------------"""
    
    def initDone(self):
        self._initDone.emit()
        
    def serverFinishedUnexpectedly(self):
        self.serverThread = None
        self.quit(EXIT_CODE_ERROR)
        
    def serverStopped(self, exitCode):
        # usually, the emitted signal won't be processed anyway (plug-ins deactivated in quit())
        if exitCode == EXIT_CODE_UPDATE:
            self.serverThread.finished.disconnect(self.serverFinishedUnexpectedly)
            self._updateRequested.emit()
        
    def memberAppended(self, ip, infoDict):
        self.memberAppendedSignal.emit(ip, infoDict)
    
    def memberUpdated(self, ip, infoDict):
        self.memberUpdatedSignal.emit(ip, infoDict)
    
    def memberRemoved(self, ip):
        self.memberRemovedSignal.emit(ip)
    
    def messagePrepended(self, messageTime, senderIP, messageText):
        self.messagePrependedSignal.emit(messageTime, [senderIP, messageText])
        
    def groupAppended(self, group, peer_groups):
        self.groupAppendedSignal.emit(group, peer_groups)

    def extendMemberInfo(self, infoDict):
        infoDict['pyqt_version'] = QtCore.PYQT_VERSION_STR
        infoDict['qt_version'] = QtCore.QT_VERSION_STR
            
    def getOpenTCPPort(self, senderIP):
        assert senderIP != None
        return DataReceiverThread.getOpenPort(category = "avatar%s" % senderIP)
    
    def receiveFile(self, ip, fileSize, fileName, tcp_port):
        self._receiveFile.emit(ip, fileSize, fileName, tcp_port)
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData = False):
        if not isData and type(fileOrData) == unicode:
            # encode to send as str
            fileOrData = fileOrData.encode('utf-8')
        self._sendFile.emit(ip, bytearray(fileOrData), otherTCPPort, isData)

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
        
        if get_settings().get_group_plugins():
            self.pluginActions = {}
            catMenus = {}
            
            allPlugins= PluginManagerSingleton.get().getAllPlugins()
            for pluginInfo in sorted(allPlugins, key=lambda info : info.name):
                categoryMenu = None
                anAction = None
                for aCat in pluginInfo.categories:
                    if aCat in catMenus:
                        categoryMenu = catMenus[aCat]
                    else:
                        categoryMenu = QMenu(aCat, plugin_menu)
                        catMenus[aCat] = categoryMenu
                
                    if anAction == None:
                        anAction = categoryMenu.addAction(pluginInfo.name)
                        anAction.setCheckable(True)
                        anAction.setChecked(pluginInfo.plugin_object.is_activated)
                        anAction.toggled.connect(partial(self.toggle_plugin, anAction, aCat))
                        self.pluginNameToMenuAction[pluginInfo.name] = anAction
                    else:
                        categoryMenu.addAction(anAction)
                    
                    if aCat in self.pluginActions:
                        self.pluginActions[aCat].append(anAction)
                    else:
                        self.pluginActions[aCat] = [anAction]
            for _cat, aMenu in sorted(catMenus.iteritems(), key = lambda aTuple : aTuple[0]):
                plugin_menu.addMenu(aMenu)
        else:
            self.pluginActions = []
            allPlugins= PluginManagerSingleton.get().getAllPlugins()
            for pluginInfo in sorted(allPlugins, key=lambda info : info.name):
                anAction = plugin_menu.addAction(pluginInfo.name)
                anAction.setCheckable(True)
                anAction.setChecked(pluginInfo.plugin_object.is_activated)
                anAction.toggled.connect(partial(self.toggle_plugin, anAction, pluginInfo.categories[0]))
                self.pluginNameToMenuAction[pluginInfo.name] = anAction
                self.pluginActions.append(anAction)
        
        #main _menu
        anAction = menu.addAction('Call for lunch')
        anAction.triggered.connect(partial(self.sendMessageClicked, u'lunch', None))
        
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
    
    @pyqtSlot()
    def updateRequested(self):
        self.quit(EXIT_CODE_UPDATE)
    
    @pyqtSlot(unicode)
    def plugin_widget_closed(self, p_name):
        # just un-check the menu item, this will cause a callback
        anAction = self.pluginNameToMenuAction[p_name]
        anAction.setChecked(False)

    @pyqtSlot(QAction, unicode, bool)
    def toggle_plugin(self,w,p_cat,new_state):
        p_cat = convert_string(p_cat)
        p_name = convert_string(w.text())
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
    
    @pyqtSlot(unicode, QObject)
    def sendMessageClicked(self, message, text):
        if message != None:
            get_server().call_all_members(convert_string(message))
        else:
            get_server().call_all_members(text)
        
    @pyqtSlot(QLineEdit)
    def addHostClicked(self, hostn):
        try:
            ip = socket.gethostbyname(hostn.strip())
            get_server()._append_member(ip, hostn)
        except:
            d = QMessageBox(QMessageBox.Critical, "Error adding host", "Cannot add host: Hostname unknown: %s" % hostn, QMessageBox.Ok, self.mainWindow)
            d.exec_()
            
    @pyqtSlot(bool)
    @pyqtSlot()
    def quitClicked(self,_ = None):
        self.quit()

    @pyqtSlot(bool)
    @pyqtSlot()
    def openWindowClicked(self, _ = None):    
        self.reset_new_msgs() 
        
        if self.mainWindow == None:
            log_error("mainWindow is not initialized")
            return
        self.mainWindow.show()
        self.mainWindow.activateWindow()
        self.mainWindow.raise_()
            
    @pyqtSlot(bool)
    @pyqtSlot()
    def openSettingsClicked(self,_ = None):
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

    @pyqtSlot(unicode, bytearray, int, bool)
    def sendFileSlot(self, addr, fileToSend, other_tcp_port, isData):
        addr = convert_string(addr)
        if isData:
            fileToSend = str(fileToSend)
        else:
            fileToSend = str(fileToSend).decode("utf-8")
        ds = DataSenderThread(self,addr,fileToSend, other_tcp_port, isData)
        ds.finished.connect(ds.deleteLater)
        ds.start()
        
    def successfullyReceivedFile(self, _thread, filePath):
        log_info("successfully received file %s" % filePath)
        
    def errorOnTransfer(self, _thread):
        log_error("Error receiving file")
    
    @pyqtSlot(unicode, int, unicode, int)
    def receiveFileSlot(self, addr, file_size, file_name, tcp_port):
        addr = convert_string(addr)
        file_name = convert_string(file_name)
        dr = DataReceiverThread(self,addr,file_size,file_name,tcp_port,category="avatar%s" % addr)
        dr.successfullyTransferred.connect(self.successfullyReceivedFile)
        dr.errorOnTransfer.connect(self.errorOnTransfer)
        dr.finished.connect(dr.deleteLater)
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
