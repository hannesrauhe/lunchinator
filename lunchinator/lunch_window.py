from PyQt4.QtGui import QTabWidget, QMainWindow, QTextEdit, QDockWidget, QApplication, QMenu, QKeySequence, QIcon
from PyQt4.QtCore import Qt, QSettings, QVariant, QEvent
from lunchinator import get_settings, get_server, log_exception, convert_string, get_plugin_manager
import sys
from StringIO import StringIO
import traceback

class PluginDockWidget(QDockWidget):
    def __init__(self, name, parent, closeCallback):
        super(PluginDockWidget, self).__init__(name, parent)
        self.closeCallback = closeCallback
        self.setAttribute(Qt.WA_DeleteOnClose)
        
    def closeEvent(self, closeEvent):
        self.closeCallback(self)
        return super(PluginDockWidget, self).closeEvent(closeEvent)

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
            self.addPluginWidgetByName(u"Simple View")
        
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

        if len(self.pluginNameToDockWidget) == 0:
            # no gui plugins activated, show about plugins
            self.addPluginWidgetByName(u"About Plugins")
        
        if self.locked:
            self.lockDockWidgets()
        
        # prevent from closing twice
        self.closed = False
            
            
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
            
    def addPluginWidgetByName(self, name):
        if not get_settings().get_plugins_enabled():
            return
        try:
            pluginInfo = get_plugin_manager().getPluginByName(name, u"gui")
            if not pluginInfo.plugin_object.is_activated:
                po = get_plugin_manager().activatePluginByName(name, u"gui")
            else:
                po = pluginInfo.plugin_object
            self.addPluginWidget(po, name)
        except:
            log_exception("while including plugins %s"%str(sys.exc_info()))
            
    def closePlugin(self, dockWidget):
        objectName = convert_string(dockWidget.objectName())
        if objectName in self.objectNameToPluginName:
            name = self.objectNameToPluginName[objectName]
            self.guiHandler.plugin_widget_closed(name)
            
    def addPluginWidget(self, po, name, makeVisible = False, noTabs = False):
        if name in self.pluginNameToDockWidget:
            # widget already visible
            return
        
        displayedName = po.get_displayed_name() if po.get_displayed_name() else name
        dockWidget = PluginDockWidget(displayedName, self, self.closePlugin)
        dockWidget.setObjectName(u"plugin.%s" % name)
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
        dockWidget.close()
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
            self.guiHandler.dehighlightIcon()
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
            #sw = QWidget(parent)
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
