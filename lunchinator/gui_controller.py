# coding: utf-8
from lunchinator import get_server, get_settings, convert_string,\
    get_notification_center, get_plugin_manager, get_peers
from lunchinator.log import getCoreLogger
from lunchinator.datathread.dt_qthread import DataReceiverThread, DataSenderThread
from lunchinator.lunch_server_controller import LunchServerController
from lunchinator.lunch_window import LunchinatorWindow
from lunchinator.lunch_settings_dialog import LunchinatorSettingsDialog
from lunchinator.utilities import getPlatform, PLATFORM_MAC, PLATFORM_WINDOWS,\
    getValidQtParent, restart, displayNotification, msecUntilNextMinute
from lunchinator.lunch_server import EXIT_CODE_UPDATE, EXIT_CODE_ERROR
from lunchinator.notification_center_qt import NotificationCenterQt
from lunchinator.notification_center import NotificationCenter
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.log.error_dialog import ErrorLogDialog

from PyQt4.QtGui import QLineEdit, QMenu, QMessageBox, QSystemTrayIcon,\
    QIcon, QCursor, QDialog
from PyQt4.QtCore import QThread, pyqtSignal, QObject,\
    QCoreApplication, QTimer, Qt, pyqtSlot
from PyQt4 import QtCore

from functools import partial
import platform, sip, socket, os, subprocess, time

class LunchServerThread(QThread):
    def __init__(self, parent):
        super(LunchServerThread, self).__init__(parent)
    
    def run(self):
        get_server().start_server()
        
class LunchinatorGuiController(QObject, LunchServerController):
    _menu = None
    # ---- SIGNALS ----------------
    _initDone = pyqtSignal()
    _performCall = pyqtSignal(object, set, set)
    _sendFile = pyqtSignal(object, bytearray, int, bool)
    _receiveFile = pyqtSignal(object, int, object, int, object, object)
    _processEvent = pyqtSignal(object, object, float, bool, bool)
    _processMessage = pyqtSignal(object, object, float, bool, bool)
    _updateRequested = pyqtSignal()
    _openWindow = pyqtSignal()
    # -----------------------------
    
    def __init__(self): 
        QObject.__init__(self)
        LunchServerController.__init__(self)
        
        getCoreLogger().info("Your PyQt version is %s, based on Qt %s", QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR)
        
        self._shuttingDown = False
        self.resetNextLunchTimeTimer = None
        self._updateAvailable = False
        self._repoUpdates = 0
        self._installUpdatesAction = None
        self._appUpdateStatusAction = None
        self._repoUpdateStatusAction = None
        self._restartAction = None
        self._restartStatusAction = None
        self._restartReason = u""
        self._highlightNewMessage = False
        self._highlightPeersReady = False
        
        self.exitCode = 0
        self.serverThread = None
        self.running = True
        get_server().initialize(self)
        
        self.pluginNameToMenuAction = {}
        
        # initialize main window
        self.mainWindow = LunchinatorWindow(self)
        self.settingsWindow = None
        self.errorDialog = ErrorLogDialog(self.mainWindow)
        self.setParent(self.mainWindow)
        
        if not self.createTrayIcon():
            return
        
        self.mainWindow.createMenuBar(self.pluginActions)
        
        # connect private signals
        self._initDone.connect(self.initDoneSlot)
        self._performCall.connect(self.performCallSlot)
        self._receiveFile.connect(self.receiveFileSlot)
        self._sendFile.connect(self.sendFileSlot)
        
        self._processEvent.connect(self.processEventSlot)
        self._processMessage.connect(self.processMessageSlot)
        self._updateRequested.connect(self.updateRequested)
        self._openWindow.connect(self.openWindowClicked)
        
        get_notification_center().connectApplicationUpdate(self._appUpdateAvailable)
        get_notification_center().connectOutdatedRepositoriesChanged(self._outdatedReposChanged)
        get_notification_center().connectUpdatesDisabled(self._updatesDisabled)
        get_notification_center().connectMessagePrepended(self._newMessage)
        get_notification_center().connectRestartRequired(self._restartRequired)
        get_notification_center().connectPluginActivated(self._pluginActivated)
        get_notification_center().connectPluginDeactivated(self._pluginDeactivated)
        
        self.serverThread = LunchServerThread(self)
        self.serverThread.finished.connect(self.serverFinishedUnexpectedly)
        self.serverThread.finished.connect(self.serverThread.deleteLater)
        self.serverThread.start()
        
    def _initNotificationCenter(self):
        NotificationCenter.setSingletonInstance(NotificationCenterQt(self))
        
    @loggingSlot(time.struct_time, object, object)
    def _newMessage(self, _messageTime, _senderID, _messageText):
        if self.mainWindow.isActiveWindow():
            # dont set highlighted if window is in foreground
            return
        self._highlightNewMessage = True
        self._highlightIcon()
        
    def windowActivated(self):
        """Called from Lunchinator window"""
        if self._highlightNewMessage:
            self._highlightNewMessage = False
            self._highlightIcon()
        
    def _highlightIcon(self):
        if self._highlightNewMessage:
            name = "lunchinatorred"
        elif self._highlightPeersReady:
            name = "lunchinatorgreen"
        else:
            name = "lunchinator"
        
        icon_file = get_settings().get_resource("images", name + (".png" if getPlatform() == PLATFORM_WINDOWS else ".svg"))
        
        icon = None
        if hasattr(QIcon, "fromTheme"):
            icon = QIcon.fromTheme(name, QIcon(icon_file))
        if not icon:
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
                    if subprocess.call(['gksu', get_settings().get_resource('bin', 'install-lunch-icons.sh') + ' lunchinator']) == 0:
                        getCoreLogger().info("restarting after icons were installed")
                        restart(getCoreLogger())
                        return False
                    else:
                        QMessageBox.critical(self.mainWindow,
                                             "Error installing icons",
                                             "The icons were not installed, there was an error.",
                                             buttons=QMessageBox.Ok,
                                             defaultButton=QMessageBox.Ok)
                        getCoreLogger().info("icons were not installed because of an error")
        
        # initialize tray icon
        self.statusicon = QSystemTrayIcon(self.mainWindow)
        # _highlightIcon sets the default icon
        self._highlightIcon()
        contextMenu = self.init_menu(self.mainWindow)
        self.statusicon.activated.connect(self.trayActivated)
        self.statusicon.setContextMenu(contextMenu)
        self.statusicon.show()
        return True
        
    @loggingSlot(QSystemTrayIcon.ActivationReason)
    def trayActivated(self, reason):
        if getPlatform() == PLATFORM_MAC:
            # Trigger is sent even though the context menu is shown.
            return
        if reason == QSystemTrayIcon.Trigger:
            self.statusicon.contextMenu().popup(QCursor.pos())
        
    def _coldShutdown(self, exitCode=0):
        # before exiting, process remaining events (e.g., pending messages like HELO_LEAVE)
        QCoreApplication.processEvents()
        QCoreApplication.exit(exitCode)
        self._shuttingDown = True
        
    def isShuttingDown(self):
        return self._shuttingDown
        
    def quit(self, exitCode=0):
        if self.mainWindow is not None:
            self.mainWindow.close()
        if self.settingsWindow is not None:
            self.settingsWindow.close()
        
        if self.serverThread != None and not sip.isdeleted(self.serverThread) and self.serverThread.isRunning():
            self.serverThread.finished.disconnect(self.serverFinishedUnexpectedly)
            get_server().stop_server()
            getCoreLogger().info("Waiting maximal 30s for server to stop...")
            # wait maximal 30s 
            if self.serverThread.wait(30000):
                getCoreLogger().info("server stopped")
            else:
                getCoreLogger().warning("server not stopped properly")
        else:
            getCoreLogger().info("server not running")
        
        if self.running:
            if get_settings().get_plugins_enabled():
                get_plugin_manager().deactivatePlugins(get_plugin_manager().getAllPlugins(), save_state=False)
                getCoreLogger().info("all plug-ins deactivated")
            if self.mainWindow is not None:
                self.mainWindow.finish()
            if self.settingsWindow is not None:
                self.settingsWindow.finish()
            self.running = False
            
        finalExitCode = 0
        if exitCode != 0:
            finalExitCode = exitCode
        elif self.exitCode != 0:
            finalExitCode = self.exitCode
        else:
            finalExitCode = get_server().exitCode
            
        get_settings().write_config_to_hd()
        DataReceiverThread.cleanup()
            
        self.exitCode = finalExitCode
        
        self._coldShutdown(finalExitCode)
        return finalExitCode
            
    """ ---------------- CALLED FROM LUNCH SERVER -----------------"""
    
    def initDone(self):
        self._initDone.emit()
        
    def call(self, msg, peerIDs, peerIPs):
        self._performCall.emit(msg, peerIDs, peerIPs)
        
    @loggingSlot()
    def serverFinishedUnexpectedly(self):
        self.serverThread = None
        self.quit(EXIT_CODE_ERROR)
        
    def serverStopped(self, exitCode):
        # usually, the emitted signal won't be processed anyway (plug-ins deactivated in quit())
        if exitCode == EXIT_CODE_UPDATE:
            self.serverThread.finished.disconnect(self.serverFinishedUnexpectedly)
            self._updateRequested.emit()    

    def extendMemberInfo(self, infoDict):
        super(LunchinatorGuiController, self).extendMemberInfo(infoDict)
        infoDict['pyqt_version'] = QtCore.PYQT_VERSION_STR
        infoDict['qt_version'] = QtCore.QT_VERSION_STR
            
    def getOpenPort(self, ip):
        return DataReceiverThread.getOpenPort(category="avatar%s" % ip)
        
    def receiveFile(self, ip, fileSize, fileName, tcp_port, successFunc=None, errorFunc=None):
        self._receiveFile.emit(ip, fileSize, fileName, tcp_port, successFunc, errorFunc)
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData=False):
        if not isData and type(fileOrData) == unicode:
            # encode to send as str
            fileOrData = fileOrData.encode('utf-8')
        self._sendFile.emit(ip, bytearray(fileOrData), otherTCPPort, isData)

    def processEvent(self, xmsg, addr, eventTime, newPeer, fromQueue):
        """ process any non-message event 
        @type xmsg: extMessageIncoming
        @type addr: unicode
        @type eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """
        self._processEvent.emit(xmsg, addr, eventTime, newPeer, fromQueue)
    
    
    def processMessage(self, xmsg, addr, eventTime, newPeer, fromQueue):
        """ process any message event, including lunch calls 
        @type cmd: unicode
        @type xmsg: extMessageIncoming
        @type addr: unicode
        @type eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """
        self._processMessage.emit(xmsg, addr, eventTime, newPeer, fromQueue)
    
    def getMainGUI(self):
        return self.mainWindow
    """ ----------------- CALLED ON MAIN THREAD -------------------"""
    
    def _updateRepoUpdateStatusAction(self):
        status = ""
        if self._repoUpdates == 1:
            status = "1 plugin repository can be updated"
        elif self._repoUpdates > 1:
            status = "%d plugin repositories can be updated" % self._repoUpdates
        self._repoUpdateStatusAction.setText(status)
            
        self._repoUpdateStatusAction.setVisible(self._repoUpdates > 0)
    
    @loggingSlot()
    def _appUpdateAvailable(self):
        self._updateAvailable = True
        if self._appUpdateStatusAction != None:
            self._appUpdateStatusAction.setVisible(True)
        self.notifyUpdates()
    
    @loggingSlot()
    def _outdatedReposChanged(self):
        self._repoUpdates = get_settings().get_plugin_repositories().getNumOutdated()
        if self._repoUpdateStatusAction != None:
            self._updateRepoUpdateStatusAction()
        self.notifyUpdates()
        
    @loggingSlot()
    def _updatesDisabled(self):
        if self._repoUpdateStatusAction != None:
            self._repoUpdateStatusAction.setVisible(False)
        if self._appUpdateStatusAction != None:
            self._appUpdateStatusAction.setVisible(False)
        if self._installUpdatesAction != None:
            self._installUpdatesAction.setVisible(False)
        self._updateAvailable = False
        
    def _hasUpdates(self):
        return self._updateAvailable or self._repoUpdates > 0
        
    @loggingSlot(object)
    def _restartRequired(self, reason):
        reason = convert_string(reason)
        if self._restartReason == reason:
            # same reason again, do not notify
            return
        
        displayNotification(u"Restart required", reason, getCoreLogger())
        
        if self._restartReason:
            # now there are multiple reasons to restart
            self._restartReason = u"Some changes need a restart"
        else:
            self._restartReason = reason
        if self._restartStatusAction != None:
            self._restartStatusAction.setText(self._restartReason)
            self._restartStatusAction.setVisible(True)
            # don't need both actions
            if not self._hasUpdates():
                self._restartAction.setVisible(True)
    
    def notifyUpdates(self):
        hasUpdates = self._hasUpdates()
        if self._installUpdatesAction != None:
            self._installUpdatesAction.setVisible(hasUpdates)
            # don't need both
            self._restartAction.setVisible(False)
    
    def _getDisplayedName(self, pluginInfo):
        return pluginInfo.plugin_object.get_displayed_name() if pluginInfo.plugin_object.get_displayed_name() else pluginInfo.name
    
    def _create_plugin_action(self, pluginInfo, parentMenu, aCat):
        displayedName = self._getDisplayedName(pluginInfo) 
        anAction = parentMenu.addAction(displayedName)
        anAction.setCheckable(True)
        anAction.setChecked(pluginInfo.plugin_object.is_activated)
        anAction.triggered.connect(partial(self.toggle_plugin, pluginInfo.name, aCat), type=Qt.DirectConnection)
        self.pluginNameToMenuAction[pluginInfo.name] = anAction
        return anAction
        
    def init_menu(self, parent):        
        # create the plugin submenu
        menu = QMenu(parent)
        plugin_menu = QMenu("PlugIns", menu)
        
        self.pluginActions = None
        if get_settings().get_plugins_enabled():
            allPlugins = [x for x in get_plugin_manager().getAllPlugins() if not x.plugin_object.is_activation_forced()]
            
            if get_settings().get_group_plugins():
                self.pluginActions = {}
                catMenus = {}
                
                for pluginInfo in sorted(allPlugins, key=lambda info : self._getDisplayedName(info)):                
                    categoryMenu = None
                    anAction = None
                    for aCat in pluginInfo.categories:
                        if aCat in catMenus:
                            categoryMenu = catMenus[aCat]
                        else:
                            categoryMenu = QMenu(aCat, plugin_menu)
                            catMenus[aCat] = categoryMenu
                    
                        if anAction == None:
                            anAction = self._create_plugin_action(pluginInfo, categoryMenu, aCat)
                        else:
                            categoryMenu.addAction(anAction)
                        
                        if aCat in self.pluginActions:
                            self.pluginActions[aCat].append(anAction)
                        else:
                            self.pluginActions[aCat] = [anAction]
                for _cat, aMenu in sorted(catMenus.iteritems(), key=lambda aTuple : aTuple[0]):
                    plugin_menu.addMenu(aMenu)
            else:
                self.pluginActions = []
                for pluginInfo in sorted(allPlugins, key=lambda info : self._getDisplayedName(info)):
                    anAction = self._create_plugin_action(pluginInfo, plugin_menu, pluginInfo.categories[0])
                    self.pluginActions.append(anAction)
        
        # main _menu
        self._memberStatusAction = menu.addAction("Initializing...")
        self._memberStatusAction.setEnabled(False)
        
        if hasattr(menu, "addSeparator"):
            menu.addSeparator()
            
        get_notification_center().connectMemberAppended(self._updateMemberStatus)
        get_notification_center().connectMemberUpdated(self._updateMemberStatus)
        get_notification_center().connectMemberRemoved(self._updateMemberStatus)
        self.memberStatusUpdateTimer = QTimer(self)
        self.memberStatusUpdateTimer.timeout.connect(self._startSyncedTimer)
        self.memberStatusUpdateTimer.start(msecUntilNextMinute())
        
        anAction = menu.addAction('Call for lunch')
        anAction.triggered.connect(partial(self.sendMessageClicked, u'lunch'))
        
        anAction = menu.addAction('Show Lunchinator')
        anAction.triggered.connect(self.openWindowClicked)
        
        anAction = menu.addAction(u"Change today's lunch time")
        anAction.triggered.connect(self.changeNextLunchTime)
        
        if hasattr(menu, "addSeparator"):
            menu.addSeparator()
        
        anAction = menu.addAction('Settings')
        anAction.triggered.connect(self.openSettingsClicked)
        
        menu.addMenu(plugin_menu)
        
        if hasattr(menu, "addSeparator"):
            menu.addSeparator()
        
        self._restartStatusAction = menu.addAction(self._restartReason)
        self._restartStatusAction.setEnabled(False)
        self._restartAction = menu.addAction("Restart")
        self._restartAction.triggered.connect(partial(restart, getCoreLogger()))
        if self._restartReason:
            self._restartStatusAction.setVisible(True)
            self._restartAction.setVisible(True)
        else:
            self._restartStatusAction.setVisible(False)
            self._restartAction.setVisible(False)
        
        self._appUpdateStatusAction = menu.addAction("Lunchinator can be updated")
        self._appUpdateStatusAction.setEnabled(False)
        self._appUpdateStatusAction.setVisible(self._updateAvailable)
        
        self._repoUpdateStatusAction = menu.addAction("")
        self._repoUpdateStatusAction.setEnabled(False)
        self._updateRepoUpdateStatusAction()
        
        self._installUpdatesAction = menu.addAction("Install updates and restart")
        self._installUpdatesAction.triggered.connect(get_notification_center().emitInstallUpdates)
        self._installUpdatesAction.setVisible(self._updateAvailable)
        
        anAction = menu.addAction('Exit')
        anAction.triggered.connect(self.quitClicked)
            
        return menu
    
    @loggingSlot()
    def _startSyncedTimer(self):
        self._updateMemberStatus()
        self.memberStatusUpdateTimer.timeout.disconnect(self._startSyncedTimer)
        self.memberStatusUpdateTimer.timeout.connect(self._updateMemberStatus)
        self.memberStatusUpdateTimer.start(60000)
    
    @pyqtSlot()
    @pyqtSlot(object)
    @loggingSlot(object, object)
    def _updateMemberStatus(self, _pID=None, _pInfo=None):
        peers = get_server().getLunchPeers()
        readyMembers = peers.getReadyMembers()
        notReadyMembers = peers.getMembers() - readyMembers
        
        # don't display members with unknown status as ready
        readyMembers = [pID for pID in readyMembers if peers.isPeerReadinessKnown(pID=pID)]
        
        everybodyReady = False
        if not readyMembers and not notReadyMembers:
            status = u"No members."
        elif not readyMembers:
            status = u"Nobody is ready for lunch."
        elif not notReadyMembers:
            everybodyReady = True
            status = u"Everybody is ready for lunch."
        else:
            if len(readyMembers) == 1:
                ready = u"1 member"
            else:
                ready = u"%d members" % len(readyMembers)
                
            if len(notReadyMembers) == 1:
                notReady = u"1 member"
            else:
                notReady = u"%d members" % len(notReadyMembers)
            
            status = u"%s ready, %s not ready for lunch." % (ready, notReady)
        if everybodyReady and not self._highlightPeersReady:
            # don't highlight if I am the only member
            if len(readyMembers) > 1 or not get_peers().isMe(pID=iter(readyMembers).next()):
                self._highlightPeersReady = True
                if get_settings().get_notification_if_everybody_ready():
                    displayNotification("Lunch Time",
                                        "Everybody is ready for lunch now",
                                        getCoreLogger(),
                                        get_settings().get_resource("images", "lunchinator.png"))
                self._highlightIcon()
            else:
                status = u"You are the only member."
        elif not everybodyReady and self._highlightPeersReady:
            self._highlightPeersReady = False
            self._highlightIcon()
        self._memberStatusAction.setText(status)
    
    def disable_auto_update(self):
        get_settings().set_auto_update_enabled(False)
                  
    def _insertMessage(self, mtime, addr, msg):
        QCoreApplication.processEvents()
        LunchServerController._insertMessage(self, mtime, addr, msg)
                  
    """---------------------- SLOTS ------------------------------"""
    
    @loggingSlot()
    def initDoneSlot(self):
        pass
    
    @loggingSlot(object, set, set)
    def performCallSlot(self, msg, peerIDs, peerIPs):
        get_server().perform_call(msg, peerIDs, peerIPs)
    
    @loggingSlot()
    def updateRequested(self):
        self.quit(EXIT_CODE_UPDATE)
    
    @loggingSlot(object, object)
    def _pluginActivated(self, pluginName, _category):
        pluginName = convert_string(pluginName)
        if pluginName in self.pluginNameToMenuAction:
            anAction = self.pluginNameToMenuAction[pluginName]
            anAction.setChecked(True)
            
    @loggingSlot(object, object)
    def _pluginDeactivated(self, pluginName, _category):
        pluginName = convert_string(pluginName)
        if pluginName in self.pluginNameToMenuAction:
            anAction = self.pluginNameToMenuAction[pluginName]
            anAction.setChecked(False)

    @loggingSlot(object, object, bool)
    def toggle_plugin(self, p_name, p_cat, new_state):
        try:
            p_cat = convert_string(p_cat)
            p_name = convert_string(p_name)
            
            if new_state:
                get_plugin_manager().activatePluginByName(p_name, p_cat)
            else:
                get_plugin_manager().deactivatePluginByName(p_name, p_cat)
        except:
            getCoreLogger().exception("Error toggling plugin")
    
    @loggingSlot(object, QObject)
    def sendMessageClicked(self, message, text):
        if message != None:
            get_server().call_all_members(convert_string(message))
        else:
            get_server().call_all_members(text)
        
    @loggingSlot(QLineEdit)
    def addHostClicked(self, hostn):
        try:
            ip = socket.gethostbyname(hostn.strip())
            get_server().call_request_info([ip])
        except:
            d = QMessageBox(QMessageBox.Critical, "Error adding host", "Cannot add host: Hostname unknown: %s" % hostn, QMessageBox.Ok, self.mainWindow)
            d.exec_()
            
    @pyqtSlot(bool)
    @loggingSlot()
    def quitClicked(self, _=None):
        self.quit()

    @pyqtSlot(bool)
    @loggingSlot()
    def openWindowClicked(self, _=None):    
        if self.mainWindow == None:
            getCoreLogger().error("mainWindow is not initialized")
            return
        self.mainWindow.showNormal()
        self.mainWindow.raise_()
        self.mainWindow.activateWindow()
            
    @loggingSlot()
    def changeNextLunchTime(self, begin = None, end = None):
        if begin == None:
            if self.mainWindow == None:
                getCoreLogger().error("mainWindow is not initialized")
                return
            from lunchinator.timespan_input_dialog import TimespanInputDialog
            dialog = TimespanInputDialog(self.mainWindow, "Change Lunch Time", "When are you free for lunch today?", get_settings().get_next_lunch_begin(), get_settings().get_next_lunch_end())
            dialog.exec_()
            if dialog.result() == QDialog.Accepted:
                get_settings().set_next_lunch_time(dialog.getBeginTimeString(), dialog.getEndTimeString())
            else:
                return        
        else:
            get_settings().set_next_lunch_time(begin, end) 
            
        if self.resetNextLunchTimeTimer != None:
            self.resetNextLunchTimeTimer.stop()
            self.resetNextLunchTimeTimer.deleteLater()
            
        td = get_settings().get_next_lunch_reset_time()
        if td > 0:
            self.resetNextLunchTimeTimer = QTimer(getValidQtParent())
            self.resetNextLunchTimeTimer.timeout.connect(self._resetNextLunchTime)
            self.resetNextLunchTimeTimer.setSingleShot(True)
            self.resetNextLunchTimeTimer.start(abs(td) + 1000)
            
        get_server().call_info()
            
    @loggingSlot()
    def _resetNextLunchTime(self):
        get_settings().set_next_lunch_time(None, None)
        get_server().call_info()
            
    @pyqtSlot(bool)
    @loggingSlot()
    def openSettingsClicked(self, _=None):
        if self.mainWindow == None:
            getCoreLogger().error("mainWindow not specified")
            return
        
        if self.settingsWindow == None:
            self.settingsWindow = LunchinatorSettingsDialog(self.mainWindow)
            self.settingsWindow.save.connect(partial(self.settingsDialogAction, True))
            self.settingsWindow.discard.connect(partial(self.settingsDialogAction, False))

        self.settingsWindow.showNormal()
        self.settingsWindow.raise_()
        self.settingsWindow.activateWindow()

    @loggingSlot()        
    def settingsDialogAction(self, saved):
        if not get_settings().get_plugins_enabled():
            return
        for pluginInfo in get_plugin_manager().getAllPlugins():
            if pluginInfo.plugin_object.is_activated and self.settingsWindow.isOptionsWidgetLoaded(pluginInfo.name):
                if saved:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data(sendInfoDict=False)
                    except:
                        getCoreLogger().exception("was not able to save data for plugin %s", pluginInfo.name)
                else:
                    pluginInfo.plugin_object.discard_changes()
        get_settings().write_config_to_hd()
            
        get_server().call_info()      

    @loggingSlot(object, bytearray, int, bool)
    def sendFileSlot(self, addr, fileToSend, other_tcp_port, isData):
        addr = convert_string(addr)
        if isData:
            fileToSend = str(fileToSend)
            ds = DataSenderThread.sendData(addr, other_tcp_port, fileToSend, getCoreLogger(), parent=self)
        else:
            fileToSend = str(fileToSend).decode("utf-8")
            ds = DataSenderThread.sendSingleFile(addr, other_tcp_port, fileToSend, getCoreLogger(), parent=self)
        ds.finished.connect(ds.deleteLater)
        ds.start()
        
    @loggingSlot(QThread, object)
    def successfullyReceivedFile(self, _thread, filePath):
        getCoreLogger().info("successfully received file %s", filePath)
        
    @loggingSlot(QThread, object)
    def errorOnTransfer(self, _thread, message):
        getCoreLogger().warning("Error receiving file (%s)", message)
    
    @loggingSlot(object, int, object, int, object, object)
    def receiveFileSlot(self, addr, file_size, file_name, tcp_port, successFunc, errorFunc):
        addr = convert_string(addr)
        file_name = convert_string(file_name)
        dr = DataReceiverThread.receiveSingleFile(addr, file_name, file_size, tcp_port, getCoreLogger(), "avatar%s" % addr, True, parent=self)
        if successFunc:
            dr.successfullyTransferred.connect(lambda _thread, _path : successFunc())
        if errorFunc:
            dr.errorOnTransfer.connect(lambda _thread, _msg : errorFunc())
        dr.successfullyTransferred.connect(self.successfullyReceivedFile)
        dr.errorOnTransfer.connect(self.errorOnTransfer)
        dr.finished.connect(dr.deleteLater)
        dr.start()
        
    @loggingSlot(object, object, float, bool, bool)
    def processEventSlot(self, xmsg, addr, eventTime, newPeer, fromQueue):
        """ process events that are not group messages
        @type xmsg: extendedMessageIncoming
        @type addr: unicode
        @type eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """
        super(LunchinatorGuiController, self).processEvent(xmsg, addr, eventTime, newPeer, fromQueue)
     
    @loggingSlot(object, object, float, bool, bool)
    def processMessageSlot(self, xmsg, addr, eventTime, newPeer, fromQueue):
        """ process any message event, including lunch calls
        @type xmsg: extendedMessageIncoming
        @type addr: unicode
        @type eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """

        super(LunchinatorGuiController, self).processMessage(xmsg, addr, eventTime, newPeer, fromQueue)
