from PyQt4.QtGui import QTabWidget, QMainWindow, QTextEdit, QLineEdit, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QApplication, QPushButton, QTreeView, QStyledItemDelegate, QItemSelectionModel
from PyQt4.QtCore import Qt, QTimer
from lunchinator import get_settings, get_server, log_exception
import sys
from StringIO import StringIO
import traceback
from functools import partial

class LunchinatorWindow(QMainWindow):
    def __init__(self):
        super(LunchinatorWindow, self).__init__(None)
        
        self.guiHandler = None
        
        #window.set_border_width(10)
        self.centerOnScreen() # TODO do this here?
        self.setWindowTitle("Lunchinator")

        # Contains box1 and plug-ins
        centralWidget = QWidget(self)
        centralLayout = QHBoxLayout(centralWidget)

        tablesPane = QSplitter(Qt.Horizontal)
        widget, self.messagesTable = self.createTableWidget(tablesPane, MessageTable, "Send Message", self.clicked_send_msg)
        tablesPane.addWidget(widget)
        widget, self.membersTable = self.createTableWidget(tablesPane, MembersTable, "Add Host", self.clicked_add_host)
        tablesPane.addWidget(widget)

        centralLayout.addWidget(tablesPane)
        #box0.pack_start(tablesPane, True, True, 0)
        
        self.nb = QTabWidget(centralWidget)
        self.nb.setMovable(True)
        self.nb.setTabPosition(QTabWidget.North)
        
        centralLayout.addWidget(self.nb)
        
        self.setCentralWidget(centralWidget)
        
    def serverInitialized(self):
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
        if get_settings().last_gui_plugin_index < len(self.nb) and get_settings().last_gui_plugin_index >= 0:
            index = get_settings().last_gui_plugin_index
        
        self.nb.setCurrentIndex(index)
        
    def clicked_send_msg(self, w):
        if self.guiHandler != None:
            self.guiHandler.clicked_send_msg(w)
            
    def clicked_add_host(self, w):
        if self.guiHandler != None:
            self.guiHandler.clicked_add_host(w)
        
    def closeEvent(self, *args, **kwargs):
        try:
            order = []
            for i in range(len(self.nb)):
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
        self.nb = None
        
        self.guiHandler.window_msgClosed(self)
        QMainWindow.closeEvent(self, *args, **kwargs)     
        
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
            # TODO append page correctly
            self.nb.addTab(widget, text)
            self.nb.setCurrentIndex(self.nb.count() - 1)
            
    def removePluginWidget(self, tabText):        
        widgetIndex = self.widgetIndex(tabText)
        if widgetIndex >= 0:
            self.nb.removeTab(widgetIndex)

    def createTableWidget(self, parent, TableClass, buttonText, triggeredEvent):
        # create HBox in VBox for each table
        # Create message table
        tableWidget = QWidget(parent)
        tableLayout = QVBoxLayout(tableWidget)
        tableBottomLayout = QHBoxLayout()
        
        table = TableClass(tableWidget)
        tableLayout.addWidget(table)
        #tableLayout.pack_start(table.scrollTree, True, True, 0)
        
        entry = QLineEdit(tableWidget)
        tableBottomLayout.addWidget(entry)
        #tableBottomLayout.pack_start(entry, True, True, 3)
        button = QPushButton(buttonText, tableWidget)
        tableBottomLayout.addWidget(button)
        #tableBottomLayout.pack_start(button, False, True, 10)
        tableLayout.addLayout(tableBottomLayout)
        #tableLayout.pack_start(tableBottomLayout, False, True, 0)
        
        entry.returnPressed.connect(partial(triggeredEvent, entry))
        button.clicked.connect(partial(triggeredEvent, entry))
        
        return (tableWidget, table)
   
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
        
class MembersTableItemDelegate(QStyledItemDelegate):
    # void paint(QPainter * painter, const QStyleOptionViewItem & option, const QModelIndex & index)
    def paint(self, painter, option, index):
        super(MembersTableItemDelegate, self).paint(painter, option, index)

class UpdatingTable(QTreeView):
    def __init__(self, parent, sortedColumn = None, ascending = True):
        super(UpdatingTable, self).__init__(parent)
        
        self.setSortingEnabled(True)
        self.setHeaderHidden(False)
        self.setAlternatingRowColors(True)
        if sortedColumn != None:
            self.sortByColumn(sortedColumn, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
    
class MembersTable(UpdatingTable):    
    def __init__(self, parent):
        UpdatingTable.__init__(self, parent, 2)
        
    def setModel(self, model):
        super(MembersTable, self).setModel(model)
        timeoutTimer = QTimer(self)
        timeoutTimer.setInterval(1000)
        timeoutTimer.timeout.connect(self.model().updateTimeouts)
        timeoutTimer.start(1000)  
        
class MessageTable(UpdatingTable):
    def __init__(self, parent):
        UpdatingTable.__init__(self, parent)      
    
    