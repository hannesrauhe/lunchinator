from PyQt4.QtGui import QTabWidget, QMainWindow, QGridLayout, QLabel, QTextEdit, QLineEdit, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QApplication, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt4.QtCore import Qt
from PyQt4 import QtCore
from lunchinator import get_settings, get_server, log_exception
import sys
import socket
from StringIO import StringIO
import traceback
import gobject
import time
from functools import partial
from Pyrex.Compiler.Parsing import p_name

class LunchinatorWindow(QMainWindow):
    def __init__(self, guiHandler):
        super(LunchinatorWindow, self).__init__(None)
        
        self.guiHandler = guiHandler
        
        #window.set_border_width(10)
        self.centerOnScreen() # TODO do this here?
        self.setWindowTitle("Lunchinator")

        # Contains box1 and plug-ins
        centralWidget = QWidget(self)
        centralLayout = QHBoxLayout(centralWidget)

        tablesPane = QSplitter(Qt.Horizontal)
        tablesPane.addWidget(self.createTableWidget(tablesPane, MessageTable, "Send Message", guiHandler.clicked_send_msg))
        tablesPane.addWidget(self.createTableWidget(tablesPane, MembersTable, "Add Host", guiHandler.clicked_add_host))

        centralLayout.addWidget(tablesPane)
        #box0.pack_start(tablesPane, True, True, 0)
        
        self.nb = QTabWidget(centralWidget)
        self.nb.setMovable(True)
        self.nb.setTabPosition(QTabWidget.North)
        
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
        centralLayout.addWidget(self.nb)
        #centralLayout.pack_start(self.nb, True, True, 0)
        
        self.setCentralWidget(centralWidget)

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
        
        return tableWidget
   
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
        
        
class UpdatingTable(QTreeWidget):
    def __init__(self, parent, nCol, headerLabels, sortedColumn = None, ascending = True):
        super(UpdatingTable, self).__init__(parent)
        
        self.setColumnCount(nCol)
        self.setHeaderLabels(headerLabels)
        if sortedColumn != None:
            self.sortItems(sortedColumn, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
        
        self.update_model()
        gobject.timeout_add(1000, self.timeout)        
    
    def listToQStringList(self, list):
        qList = QtCore.QStringList()
        for aStr in list:
            qList.append(aStr if type(aStr) in (str, unicode) else str(aStr))
        return qList
        
    def timeout(self):
        try:
            #sortCol,sortOrder = self.treeView.get_model().get_sort_column_id()
            self.update_model()
            #if sortCol!=None:
            #    st.set_sort_column_id(sortCol,sortOrder)
            #self.treeView.set_model(self.listStore)
            return True
        except:
            return False
    
    def create_model(self):
        return None
    
    def update_model(self):
        pass
    
class MembersTable(UpdatingTable):    
    def __init__(self, parent):
        # TODO fifth column?
        UpdatingTable.__init__(self, parent, 5, ["IP", "Name", "LunchTime", "LastSeen", "Stuff"], 2)        
    
    
    def update_model(self):
        self.clear()
        me = get_server().get_members()
        ti = get_server().get_member_timeout()
        inf = get_server().get_member_info()
        for ip in me.keys():
            member_entry=[ip,me[ip],"-",-1,"#FFFFFF"]
            if inf.has_key(ip) and inf[ip].has_key("next_lunch_begin") and inf[ip].has_key("next_lunch_end"):
                member_entry[2]=inf[ip]["next_lunch_begin"]+"-"+inf[ip]["next_lunch_end"]  
                if get_server().is_now_in_time_span(inf[ip]["next_lunch_begin"],inf[ip]["next_lunch_end"]):
                    member_entry[4]="#00FF00"
                else:
                    member_entry[4]="#FF0000"
            if ti.has_key(ip):
                member_entry[3]=int(time.time()-ti[ip])
            self.addTopLevelItem(QTreeWidgetItem(self.listToQStringList(member_entry)))     
    
class MessageTable(UpdatingTable):
    def __init__(self, parent):
        UpdatingTable.__init__(self, parent, 3, ["Time", "Sender", "Message"])     
    
    def update_model(self):
        m = get_server().get_last_msgs()
        self.clear()
        for i in m:
            if i[1] in get_server().get_members():
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),get_server().get_members()[i[1]],i[2])
            else:
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),i[1],i[2])
            self.addTopLevelItem(QTreeWidgetItem(self.listToQStringList(i)))
    
    
    