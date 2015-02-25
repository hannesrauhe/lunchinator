from PyQt4.QtCore import Qt
from PyQt4.QtGui import QComboBox, QWidget, QGridLayout, QLabel, QStackedWidget, QPushButton,\
    QInputDialog, QLineEdit
from copy import deepcopy
from lunchinator import get_plugin_manager, convert_string
from lunchinator.log.logging_slot import loggingSlot

class DbConnOptions(QWidget):
    def __init__(self, parent, conn_properties):        
        super(DbConnOptions, self).__init__(parent)
        
        self.plugin_manager = get_plugin_manager()
        self.available_types = {}
        self.conn_properties = None
        self.conn_passwords = None
        
        for dbplugin in self.plugin_manager.getPluginsOfCategory("db"):
            self.available_types[dbplugin.name] = dbplugin.plugin_object
                
        lay = QGridLayout(self)
        
        if len(self.available_types) == 0:
            lay.addWidget(QLabel("No DB plugin activated", parent), 0, 0, Qt.AlignRight)
            return
            
        lay.addWidget(QLabel("Name: ", parent), 0, 0, Qt.AlignRight)        
        self.nameCombo = QComboBox(parent)
        lay.addWidget(self.nameCombo, 0, 1)
        lay.addWidget(QLabel("Type: ", parent), 1, 0, Qt.AlignRight)
        self.typeCombo = QComboBox(parent)
        lay.addWidget(self.typeCombo, 1, 1)
        self.conn_details = QStackedWidget(parent)
        lay.addWidget(self.conn_details, 2, 0, 1, 2)        
        newConnButton = QPushButton("New Connection", parent)
        lay.addWidget(newConnButton, 3, 1)
        self.warningLbl = QLabel("The standard connection is used by the lunchinator internally to store messages etc." + \
                             " It can be used by plugins as well, but it cannot be changed.")
        self.warningLbl.setWordWrap(True)
        lay.addWidget(self.warningLbl, 4, 0, 4, 2)
        
        for p in self.available_types.values():
            w = p.create_db_options_widget(parent)
            if w == None:
                w = QLabel("Plugin not activated", parent)
            self.conn_details.addWidget(w)   
            
        self.typeCombo.addItems(self.available_types.keys())
        
        self.reset_connection_properties(conn_properties)  
        newConnButton.clicked.connect(self.new_conn)      
        
    def reset_connection_properties(self, conn_properties):
        try:
            self.nameCombo.currentIndexChanged.disconnect(self.name_changed)
            self.typeCombo.currentIndexChanged.disconnect(self.type_changed)
        except:
            pass
        
        self.conn_properties = deepcopy(conn_properties)
        self.conn_passwords = {}
        for connName in self.conn_properties:
            self.conn_passwords[connName] = {}
        
        self.nameCombo.clear()
        self.nameCombo.addItems(self.conn_properties.keys())
            
        type_name = self.conn_properties[str(self.nameCombo.currentText())]["plugin_type"]
        type_index = self.typeCombo.findText(type_name)
        self.typeCombo.setCurrentIndex(type_index)  
        self.conn_details.setCurrentIndex(type_index)
        
        self.fill_conn_details()       
        
        self.typeCombo.currentIndexChanged.connect(self.type_changed)
        self.nameCombo.currentIndexChanged.connect(self.name_changed)
    
    def store_conn_details(self):
        p = self.available_types[self.last_type]
        p.save_options_widget_data() # this doesn't write anything to the config file
        o = p.getOptions()
        
        self.conn_passwords[self.last_name].update(p.getPasswords())
        p.clearPasswords()
        if o:
            self.conn_properties[self.last_name].update(o)
            self.conn_properties[self.last_name]["plugin_type"] = self.last_type
        
    def fill_conn_details(self):        
        self.last_type = convert_string(self.typeCombo.currentText())
        self.last_name = convert_string(self.nameCombo.currentText())
        
        p = self.available_types[self.last_type]
        
        p.setConnection(self.last_name, self.conn_properties[self.last_name], self.conn_passwords[self.last_name].keys())
            
        if self.nameCombo.currentText()=="Standard":
            self.typeCombo.setEnabled(False)
            self.conn_details.setEnabled(False)
            self.warningLbl.setVisible(True)
        else:
            self.typeCombo.setEnabled(True)
            self.conn_details.setEnabled(True)
            self.warningLbl.setVisible(False)
        
    @loggingSlot(int)
    def type_changed(self, index):
        self.conn_details.setCurrentIndex(index)
        self.store_conn_details()
        self.fill_conn_details()
        
    @loggingSlot(int)
    def name_changed(self, _index):
        type_name = self.conn_properties[str(self.nameCombo.currentText())]["plugin_type"]
        type_index = self.typeCombo.findText(type_name)
        if type_index == self.typeCombo.currentIndex():
            self.store_conn_details()
            self.fill_conn_details()
        else:
            self.typeCombo.setCurrentIndex(type_index)
            
    @loggingSlot()
    def new_conn(self):
        i = len(self.conn_properties)
        while u"Conn %d" % i in self.conn_properties:
            i += 1
        proposedName = u"Conn %d" % i
        
        new_conn_name = None
        while not new_conn_name or new_conn_name in self.conn_properties:
            if new_conn_name in self.conn_properties:
                msg = u"Connection \"%s\" already exists. Enter a different name:" % new_conn_name
            else:
                msg = u"Enter the name of the new connection:"
            new_conn_name, ok = QInputDialog.getText(self,
                                                     u"Connection Name",
                                                     msg,
                                                     QLineEdit.Normal,
                                                     proposedName)
            if not ok:
                return 
            new_conn_name = convert_string(new_conn_name)
        
        self.conn_properties[new_conn_name] = {"plugin_type" : convert_string(self.typeCombo.currentText()) }
        self.conn_passwords[new_conn_name] = {}
        self.nameCombo.addItem(new_conn_name)
        self.nameCombo.setCurrentIndex(self.nameCombo.count() - 1)
        
    def get_connection_properties(self):
        self.store_conn_details()
        return self.conn_properties, self.conn_passwords

    def clear_passwords(self):
        for connName in self.conn_passwords:
            self.conn_passwords[connName] = {}
        