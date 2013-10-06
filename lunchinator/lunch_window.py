from PyQt4.QtGui import QTabWidget, QMainWindow, QTextEdit, QApplication
from lunchinator import get_settings, get_server, log_exception
import sys
from StringIO import StringIO
import traceback

class LunchinatorWindow(QMainWindow):
    def __init__(self, controller):
        super(LunchinatorWindow, self).__init__(None)
        
        self.guiHandler = controller
        self.setWindowTitle("Lunchinator")

        self.nb = QTabWidget(self)
        self.nb.setMovable(True)
        self.nb.setTabPosition(QTabWidget.North)
        
        self.setCentralWidget(self.nb)
        
        # add plugins
        plugin_widgets = []
        try:
            for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    plugin_widgets.append((pluginInfo,self.window_msgCheckCreatePluginWidget(self.nb, pluginInfo.plugin_object, pluginInfo.name)))
            if len(plugin_widgets) == 0:
                #activate help plugin
                get_server().plugin_manager.activatePluginByName("About Plugins", "gui")
                pluginInfo = get_server().plugin_manager.getPluginByName("About Plugins", "gui")
                if pluginInfo != None:
                    plugin_widgets.append((pluginInfo,self.window_msgCheckCreatePluginWidget(self.nb, pluginInfo.plugin_object, pluginInfo.name)))
                pass                    
        except:
            log_exception("while including plugins %s"%str(sys.exc_info()))
            
        plugin_widgets.sort(key=lambda tup: tup[0].name)
        plugin_widgets.sort(key=lambda tup: tup[0].plugin_object.sortOrder)
        
        for info,widget in plugin_widgets:
            self.nb.addTab(widget, info.name)
        
        # select previously selected widget
        index = 0
        if get_settings().get_last_gui_plugin_index() < self.nb.count() and get_settings().get_last_gui_plugin_index() >= 0:
            index = get_settings().get_last_gui_plugin_index()
        
        self.nb.setCurrentIndex(index)
        self.centerOnScreen()
        # prevent from closing twice
        self.closed = False
        
    def closeEvent(self, closeEvent):
        if not self.closed:
            self.closed = True
            try:
                order = []
                for i in range(self.nb.count()):
                    order.append(self.nb.tabText(i))
                for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                    # store sort order
                    if pluginInfo.name in order:
                        pluginInfo.plugin_object.sortOrder = order.index(pluginInfo.name)
                        pluginInfo.plugin_object.save_sort_order()
                    if pluginInfo.plugin_object.is_activated:
                        pluginInfo.plugin_object.destroy_widget()
                        
                if self.nb != None:
                    get_settings().set_last_gui_plugin_index(self.nb.currentIndex())
            except:
                log_exception("while storing order of GUI plugins:\n  %s", str(sys.exc_info()))
        
        QMainWindow.closeEvent(self, closeEvent)     
        
    def centerOnScreen(self):
        r = self.geometry()
        r.moveCenter(QApplication.desktop().availableGeometry().center())
        self.setGeometry(r)
    
    def widgetIndex(self, tabText):
        index = -1
        for i in range(self.nb.count()):
            curText = self.nb.tabText(i)
            if curText == tabText:
                index = i
                break
        return index
    
    def addPluginWidget(self, po, text):
        #check if widget is already present
        if self.widgetIndex(text) == -1:
            widget = self.window_msgCheckCreatePluginWidget(self.nb, po, text)   
            self.nb.addTab(widget, text)
            self.nb.setCurrentIndex(self.nb.count() - 1)
            
    def removePluginWidget(self, tabText):        
        widgetIndex = self.widgetIndex(tabText)
        if widgetIndex >= 0:
            self.nb.removeTab(widgetIndex)

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
