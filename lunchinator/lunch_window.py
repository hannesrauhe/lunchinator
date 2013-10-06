from PyQt4.QtGui import QTabWidget, QMainWindow, QTextEdit, QApplication, QDockWidget, QApplication, QMenu, QKeySequence
from PyQt4.QtCore import Qt, QSettings, QVariant
from lunchinator import get_settings, get_server, log_exception, convert_string
import sys, os
from StringIO import StringIO
import traceback

class PluginDockWidget(QDockWidget):
    def __init__(self, name, parent, closeCallback):
        super(PluginDockWidget, self).__init__(name, parent)
        self.closeCallback = closeCallback
        
    def closeEvent(self, _closeEvent):
        self.closeCallback(self)
        #return super(PluginDockWidget, self).closeEvent(closeEvent)

class LunchinatorWindow(QMainWindow):
    def __init__(self, controller):
        super(LunchinatorWindow, self).__init__(None)

        self.guiHandler = controller
        self.setWindowTitle("Lunchinator")

        self.setDockNestingEnabled(True)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        
        self.pluginNameToDockWidget = {}
        self.objectNameToPluginName = {}
        self.settings = QSettings(get_settings().get_main_config_dir() + os.sep + u"gui_settings.ini", QSettings.IniFormat)
        
        savedGeometry = self.settings.value("geometry", None)
        savedState = self.settings.value("state", None)
        self.locked = self.settings.value("locked", QVariant(False)).toBool()
        
        if savedState == None:
            # first run, create initial state
            self.addPluginWidgetByName(u"Messages")
            self.addPluginWidgetByName(u"Members")
            
            # check if an old-stype plugins are enabled, if not, display "about plugins"
            foundOldStylePlugin = False
            for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.name not in ("Messages", "Members") and pluginInfo.plugin_object.is_activated:
                    foundOldStylePlugin = True
            
            if not foundOldStylePlugin:
                self.addPluginWidgetByName(u"About Plugins")
        
        # add plugins
        try:
            for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    self.addPluginWidget(pluginInfo.plugin_object, pluginInfo.name)
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
            
    def createMenuBar(self, pluginActions):
        menuBar = self.menuBar()
        
        windowMenu = QMenu("Window", menuBar)
        windowMenu.addAction("Lock Widgets", self.lockDockWidgets)
        windowMenu.addAction("Unlock Widgets", self.unlockWidgets)
        windowMenu.addSeparator()
        windowMenu.addAction("Close", self.close, QKeySequence(QKeySequence.Close))
        menuBar.addMenu(windowMenu)
        
        pluginMenu = QMenu("PlugIns", menuBar)
        for anAction in pluginActions:
            pluginMenu.addAction(anAction)
        menuBar.addMenu(pluginMenu)
            
    def lockDockWidgets(self):
        self.locked = True
        for aDockWidget in self.pluginNameToDockWidget.values():
            aDockWidget.setFeatures(aDockWidget.features() & ~(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable))
            
    def unlockWidgets(self):
        self.locked = False
        for aDockWidget in self.pluginNameToDockWidget.values():
            aDockWidget.setFeatures(aDockWidget.features() | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            
    def addPluginWidgetByName(self, name):
        try:
            pluginInfo = get_server().plugin_manager.getPluginByName(name, u"gui")
            if not pluginInfo.plugin_object.is_activated:
                po = get_server().plugin_manager.activatePluginByName(name, u"gui")
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
            
    def addPluginWidget(self, po, name, makeVisible = False):
        if name in self.pluginNameToDockWidget:
            # widget already visible
            return
        
        dockWidget = PluginDockWidget(name, self, self.closePlugin)
        dockWidget.setObjectName(u"plugin.%s" % name)
        newWidget = self.window_msgCheckCreatePluginWidget(dockWidget, po, name)
        dockWidget.setWidget(newWidget)
        self.pluginNameToDockWidget[name] = dockWidget
        self.objectNameToPluginName[convert_string(dockWidget.objectName())] = name.decode()

        widgetToTabify = None
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
         
    def closeEvent(self, closeEvent):
        if not self.closed:
            self.closed = True
            try:
                order = []
                
                self.settings.setValue("geometry", self.saveGeometry())
                self.settings.setValue("state", self.saveState())
                self.settings.setValue("locked", QVariant(self.locked))
                self.settings.sync()
                for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                    # store sort order
                    if pluginInfo.name in order:
                        pluginInfo.plugin_object.sortOrder = order.index(pluginInfo.name)
                        pluginInfo.plugin_object.save_sort_order()
                    if pluginInfo.plugin_object.is_activated:
                        pluginInfo.plugin_object.destroy_widget()
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
