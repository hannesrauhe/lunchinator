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
        values = [get_settings().get_group()]+get_server().get_groups().values()
        for group in set(values):
            self.dropdown_groups_model.appendRow(QStandardItem(group))        
        self.dropdown_groups.setModel(self.dropdown_groups_model)
        log_debug("Group added to dropdown")
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QComboBox, QStandardItemModel, QStandardItem, QWidget, QVBoxLayout, QLabel, QSizePolicy
        from PyQt4.QtCore import QTimer, Qt

        iface_gui_plugin.create_widget(self, parent)        
        
        widget = QWidget(parent)
        self.dropdown_groups = QComboBox(widget)
        self.add_group()
        
        get_server().controller.groupAppendedSignal.connect(self.add_group)
        #widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)        
        return widget
    
    def add_menu(self,menu):
        pass
