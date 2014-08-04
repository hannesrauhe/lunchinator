from PyQt4.QtGui import QTabWidget, QMainWindow, QTextEdit, QDockWidget, QApplication, QMenu, QKeySequence, QIcon
from PyQt4.QtCore import Qt, QSettings, QVariant, QEvent, pyqtSignal
from lunchinator import get_settings, log_exception, convert_string, get_plugin_manager, get_notification_center
import sys
from StringIO import StringIO
import traceback

class PluginDockWidget(QDockWidget):
    closePressed = pyqtSignal(unicode) # plugin name
    
    def __init__(self, pluginName, displayedName, parent):
        super(PluginDockWidget, self).__init__(displayedName, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._pluginName = pluginName
        self._emitOnClose = True
        
    def closeEvent(self, closeEvent):
        if self._emitOnClose:
            self._emitOnClose = False
            self.closePressed.emit(self._pluginName)
            closeEvent.ignore()
        else:
            closeEvent.accept()
            
    def closeFromOutside(self):
        self._emitOnClose = False
        self.close()

class LunchinatorWindow(QMainWindow):
    def __init__(self, controller):
        super(LunchinatorWindow, self).__init__(None)

        self.guiHandler = controller
        self.setWindowTitle("Lunchinator")
        self.setWindowIcon(QIcon(get_settings().get_resource("images", "lunchinator.png"))) 

        self.setDockNestingEnabled(True)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        
        self.pluginNameToDockWidget = {}
        self.objectNameToPluginName = {}
        self.pluginNameToMenus = {}
        self.settings = QSettings(get_settings().get_config("gui_settings.ini"), QSettings.IniFormat)
        
        savedGeometry = self.settings.value("geometry", None)
        savedState = self.settings.value("state", None)
        self.locked = self.settings.value("locked", QVariant(False)).toBool()
        
        self._prepareMenuBar()
        
        if savedState == None:
            # first run, create initial state
            get_plugin_manager().activatePluginByName(u"Simple View", "gui")
            get_plugin_manager().activatePluginByName(u"Auto Update", "gui")
        
        # add plugins
        try:
            if get_settings().get_plugins_enabled():
                for pluginInfo in get_plugin_manager().getPluginsOfCategory("gui"):
                    if pluginInfo.plugin_object.is_activated:
                        self.addPluginWidget(pluginInfo.plugin_object, pluginInfo.name, noTabs=True)
        except:
            log_exception("while including plugins %s"%str(sys.exc_info()))
        
        if savedGeometry != None:
            self.restoreGeometry(savedGeometry.toByteArray())
        else:
            self.centerOnScreen()
        
        if savedState != None:
            self.restoreState(savedState.toByteArray())

        get_notification_center().connectPluginActivated(self._pluginActivated)
        get_notification_center().connectPluginWillBeDeactivated(self._pluginWillBeDeactivated)
        
        if len(self.pluginNameToDockWidget) == 0:
            # no gui plugins activated, show about plugins
            get_plugin_manager().activatePluginByName(u"About Plugins", "gui")
        
        if self.locked:
            self.lockDockWidgets()
        
        # prevent from closing twice
        self.closed = False

    def finish(self):
        get_notification_center().disconnectPluginActivated(self._pluginActivated)
        get_notification_center().disconnectPluginWillBeDeactivated(self._pluginWillBeDeactivated)
    
    def _pluginActivated(self, pName, pCat):
        pName = convert_string(pName)
        pCat = convert_string(pCat)
        if pCat == "gui":
            try:
                pluginInfo = get_plugin_manager().getPluginByName(pName, u"gui")
                self.addPluginWidget(pluginInfo.plugin_object, pName)
            except:
                log_exception("while including plugins %s"%str(sys.exc_info()))
            
    def _pluginWillBeDeactivated(self, pName, pCat):
        pName = convert_string(pName)
        pCat = convert_string(pCat)
        if pCat == "gui":
            pluginInfo = get_plugin_manager().getPluginByName(pName, pCat)
            try:
                pluginInfo.plugin_object.destroy_widget()
            except:
                log_exception("Error destroying plugin widget for plugin", pName)
            self.removePluginWidget(pName)
            
    def _prepareMenuBar(self):
        self.windowMenu = QMenu("Window", self.menuBar())
        self.menuBar().addMenu(self.windowMenu)
        
        self.pluginMenu = QMenu("PlugIns", self.menuBar())
        self.menuBar().addMenu(self.pluginMenu)
        
    def createMenuBar(self, pluginActions):
        self.windowMenu.addAction("Lock Widgets", self.lockDockWidgets)
        self.windowMenu.addAction("Unlock Widgets", self.unlockWidgets)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction("Settings", self.guiHandler.openSettingsClicked)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction("Close Window", self.close, QKeySequence(QKeySequence.Close))
        self.windowMenu.addAction("Exit Lunchinator", self.guiHandler.quit)
        
        if type(pluginActions) == list:
            for anAction in pluginActions:
                self.pluginMenu.addAction(anAction)
        elif type(pluginActions) == dict:
            for cat, actionList in sorted(pluginActions.iteritems(), key = lambda aTuple : aTuple[0]):
                catMenu = QMenu(cat, self.pluginMenu)
                for anAction in actionList:
                    catMenu.addAction(anAction)
                self.pluginMenu.addMenu(catMenu)
            
    def lockDockWidgets(self):
        self.locked = True
        for aDockWidget in self.pluginNameToDockWidget.values():
            aDockWidget.setFeatures(aDockWidget.features() & ~(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable))
            
    def unlockWidgets(self):
        self.locked = False
        for aDockWidget in self.pluginNameToDockWidget.values():
            aDockWidget.setFeatures(aDockWidget.features() | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            
    def _dockWidgetClosed(self, pluginName):
        get_plugin_manager().deactivatePluginByName(pluginName, "gui")
            
    def addPluginWidget(self, po, name, makeVisible = False, noTabs = False):
        if name in self.pluginNameToDockWidget:
            # widget already visible
            return
        
        displayedName = po.get_displayed_name() if po.get_displayed_name() else name
        dockWidget = PluginDockWidget(name, displayedName, self)
        dockWidget.setObjectName(u"plugin.%s" % name)
        dockWidget.closePressed.connect(self._dockWidgetClosed, type=Qt.QueuedConnection)
        newWidget = self.window_msgCheckCreatePluginWidget(dockWidget, po, name)
        dockWidget.setWidget(newWidget)
        self.pluginNameToDockWidget[name] = dockWidget
        self.objectNameToPluginName[convert_string(dockWidget.objectName())] = name.decode()
        
        try:
            menus = po.create_menus(self.menuBar())
            if menus:
                self.pluginNameToMenus[name] = menus
                for aMenu in menus:
                    self.menuBar().addMenu(aMenu)
        except:
            log_exception("while creating menu for plugin %s: %s" % (name, str(sys.exc_info())))

        widgetToTabify = None
        if not noTabs:
            for aDockWidget in self.pluginNameToDockWidget.values():
                tabified = self.tabifiedDockWidgets(aDockWidget)
                if len(tabified) > 0:
                    widgetToTabify = aDockWidget
                    break
            
            if widgetToTabify == None:
                for aDockWidget in self.pluginNameToDockWidget.values():
                    if self.objectNameToPluginName[convert_string(aDockWidget.objectName())] not in (u"Members", u"Messages", name):
                        widgetToTabify = aDockWidget
                        break
        
        if widgetToTabify != None:
            dockArea = self.dockWidgetArea(widgetToTabify)
            self.addDockWidget(dockArea, dockWidget)
            self.tabifyDockWidget(widgetToTabify, dockWidget)
            if makeVisible:
                QApplication.processEvents()
                dockWidget.raise_()
        else:
            self.addDockWidget(Qt.TopDockWidgetArea, dockWidget)
       
    def removePluginWidget(self, name):
        if not name in self.pluginNameToDockWidget:
            return
        
        dockWidget = self.pluginNameToDockWidget[name]
        del self.objectNameToPluginName[convert_string(dockWidget.objectName())]
        del self.pluginNameToDockWidget[name]
        dockWidget.closeFromOutside()
        if name in self.pluginNameToMenus:
            for aMenu in self.pluginNameToMenus[name]:
                self.menuBar().removeAction(aMenu.menuAction())
            del self.pluginNameToMenus[name]
         
    def setVisible(self, visible):
        if visible:
            self.closed = False
        return QMainWindow.setVisible(self, visible)

    def event(self, event):
        if event.type() == QEvent.WindowActivate:
            self.guiHandler.windowActivated()
        return QMainWindow.event(self, event)
         
    def closeEvent(self, closeEvent):
        if not self.closed:
            self.closed = True
            try:
                self.settings.setValue("geometry", self.saveGeometry())
                self.settings.setValue("state", self.saveState())
                self.settings.setValue("locked", QVariant(self.locked))
                self.settings.sync()
            except:
                log_exception("while storing order of GUI plugins:\n  %s", str(sys.exc_info()))
        
        QMainWindow.closeEvent(self, closeEvent)     
        
    def centerOnScreen(self):
        r = self.geometry()
        r.moveCenter(QApplication.desktop().availableGeometry().center())
        self.setGeometry(r)

    def window_msgCheckCreatePluginWidget(self,parent,plugin_object,p_name):
        sw = None
        try:
            sw = plugin_object.create_widget(parent)
        except:
            stringOut = StringIO()
            traceback.print_exc(None, stringOut)
            log_exception("while including plugin %s with options: %s  %s"%(p_name, str(plugin_object.options), str(sys.exc_info())))
            sw = QTextEdit(parent)
            #sw.set_size_request(400,200)
            sw.setLineWrapMode(QTextEdit.WidgetWidth)
            sw.setPlainText(stringOut.getvalue())
            stringOut.close() 
        return sw
