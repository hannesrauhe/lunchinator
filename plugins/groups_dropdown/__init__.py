from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_debug, log_exception, log_error, get_settings, get_server
import urllib2,sys
                
class groups_dropdown(iface_gui_plugin):
    def __init__(self):
        super(groups_dropdown, self).__init__()
        self.dropdown_groups_model = None
        self.dropdown_groups = None
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def do_groups(self):
        print get_server().get_groups()
        
    def add_group(self):
        from PyQt4.QtGui import QStandardItem, QStandardItemModel
        self.dropdown_groups_model = QStandardItemModel()
        values = [get_settings().get_group()]+list(get_server().get_groups())
        for group in set(values):
            self.dropdown_groups_model.appendRow(QStandardItem(group))        
        self.dropdown_groups.setModel(self.dropdown_groups_model)
        log_debug("Group added to dropdown")
        
    def change_group(self,w):
        get_server().changeGroup(unicode(self.dropdown_groups.currentText()))
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QComboBox, QStandardItemModel, QStandardItem, QWidget, QHBoxLayout, QLabel, QSizePolicy, QPushButton
        from PyQt4.QtCore import QTimer, Qt

        iface_gui_plugin.create_widget(self, parent)        
        
        widget = QWidget(parent)
        self.dropdown_groups = QComboBox(widget)
        self.dropdown_groups.setEditable(True)
        self.but = QPushButton("Change Group", widget)
        self.add_group()
        
        layout = QHBoxLayout(widget)
        layout.addWidget(self.dropdown_groups)
        layout.addWidget(self.but)
        
        self.but.clicked.connect(self.change_group)
        
        get_server().controller.groupAppendedSignal.connect(self.add_group)
        
        widget.setMaximumHeight(widget.sizeHint().height())
        widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)        
        return widget
    
    def add_menu(self,menu):
        pass
