from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGroupBox, QComboBox, QWidget, QGridLayout, QLabel, QStackedWidget, QPushButton
from lunchinator.yapsy.PluginManager import PluginManagerSingleton
from copy import deepcopy
        

class DbConnOptions(QWidget):
    def __init__(self, parent, conn_properties):        
        super(DbConnOptions, self).__init__(parent)
        
        self.conn_properties = deepcopy(conn_properties)
        self.plugin_manager = PluginManagerSingleton.get()
        self.available_types = {}
        for dbplugin in self.plugin_manager.getPluginsOfCategory("db"):
            self.available_types[dbplugin.name] = dbplugin.plugin_object
                
        lay = QGridLayout(self)
        
        if len(self.available_types)==0:
            lay.addWidget(QLabel("No DB plugin activated",parent),0,0, Qt.AlignRight)
            return
            
        lay.addWidget(QLabel("Name: ",parent),0,0, Qt.AlignRight)        
        self.nameCombo = QComboBox(parent)
        lay.addWidget(self.nameCombo,0,1)
        lay.addWidget(QLabel("Type: ",parent),1,0, Qt.AlignRight)
        self.typeCombo = QComboBox(parent)
        lay.addWidget(self.typeCombo,1,1)
        self.conn_details = QStackedWidget(parent)
        lay.addWidget(self.conn_details,2,0,1,2)        
        newConnButton = QPushButton("New Connection", parent)
        lay.addWidget(newConnButton,3,1)
        
        self.nameCombo.addItems(conn_properties.keys())
        self.typeCombo.addItems(self.available_types.keys())
        for p in self.available_types.values():
            w = p.create_db_options_widget(parent)
            if not w:
                w = QLabel("Plugin not activated",parent)
            self.conn_details.addWidget(w)   
        
        type_name = self.conn_properties[str(self.nameCombo.currentText())]["plugin_type"]
        type_index = self.typeCombo.findText(type_name)
        self.typeCombo.setCurrentIndex(type_index)     
        
        newConnButton.clicked.connect(self.new_conn)
        self.typeCombo.currentIndexChanged.connect(self.type_changed)
        self.nameCombo.currentIndexChanged.connect(self.name_changed)
        
        self.last_name = str(self.nameCombo.currentText())
        self.last_type = str(self.typeCombo.currentText())
        self.fill_conn_details()
    
    def store_conn_details(self):
        p = self.available_types[self.last_type]
        o = p.get_options_from_widget()
        if o:
            self.conn_properties[self.last_name].update(o)
            self.conn_properties[self.last_name]["plugin_type"] = self.last_type
        
    def fill_conn_details(self):        
        self.last_type = str(self.typeCombo.currentText())
        self.last_name = str(self.nameCombo.currentText())
        
        p = self.available_types[self.last_type]
        p.fill_options_widget(self.conn_properties[self.last_name])
        
    def type_changed(self, index):
        self.conn_details.setCurrentIndex(index)
        self.store_conn_details()
        self.fill_conn_details()
        
    def name_changed(self, index):
        type_name = self.conn_properties[str(self.nameCombo.currentText())]["plugin_type"]
        type_index = self.typeCombo.findText(type_name)
        if type_index == self.typeCombo.currentIndex():
            self.store_conn_details()
            self.fill_conn_details()
        else:
            self.typeCombo.setCurrentIndex(type_index)
    
    def new_conn(self):
        new_conn_name = "Conn %d"%len(self.conn_properties)
        self.conn_properties[new_conn_name] = {"plugin_type" : str(self.typeCombo.currentText()) }
        self.nameCombo.addItem(new_conn_name)
        self.nameCombo.setCurrentIndex(self.nameCombo.count()-1)
        
    def get_connection_properties(self):
        self.store_conn_details()
        return self.conn_properties