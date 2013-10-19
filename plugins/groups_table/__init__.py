from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, log_error, get_settings, get_server
import urllib2,sys
from lunchinator.table_models import TableModelBase
                
class groups_table(iface_gui_plugin):
    def __init__(self):
        super(groups_table, self).__init__()
        self.groupsTable = None
        self.times_called=0
        self.last_key=-1
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def do_groups(self):
        print get_server().get_groups()
        
    def empty(self,key,data,item):
        if key!=self.last_key:
            self.last_key=key
            self.times_called=0
        item.setText(str(data[self.times_called]))
        self.times_called+=1  
        
    def addGroupClicked(self, text):
        from PyQt4.QtGui import QMessageBox
        from lunchinator.table_models import TableModelBase
        
        columns = [("IP",self.empty),("Group",self.empty)]
        mod = TableModelBase(get_server(), columns)
        for i,ip_group in enumerate(get_server().get_groups().iteritems()):
            mod.appendContentRow(i,ip_group)
        self.groupsTable.setModel(mod)
        return True   
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import QTimer, Qt
        from lunchinator.table_widget import TableWidget        
        self.groupsTable = TableWidget(parent, "Add Group", self.addGroupClicked, sortedColumn=2, placeholderText="Enter hostname")
        
        return self.groupsTable
    
    def add_menu(self,menu):
        pass

