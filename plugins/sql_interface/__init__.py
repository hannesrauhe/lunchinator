from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server
import urllib2,sys
    
class sql_interface(iface_gui_plugin):
    def __init__(self):
        super(sql_interface, self).__init__()
        self.sqlResultTable = None
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def empty(self,*r):
        pass
        
    def sendSqlClicked(self, w):
        from lunchinator import convert_string
        from lunchinator.table_models import TableModelBase
        header, res = get_server().getDBConnection().queryWithHeader(convert_string(w.text()))
        print res
        
        columns = []
        for h in header:
            columns.append((h,self.empty))
        mod = TableModelBase(get_server(), columns)
        for i,r in enumerate(res):
            mod.appendContentRow(i, r)
        self.resultTable.setModel(mod)
#        if get_server().controller != None:
#            get_server().controller.sendMessageClicked(None, w)

#        self.messagesModel = MessagesTableModel(get_server())
#        self.messagesTable.setModel(self.messagesProxyModel)
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import Qt
        from lunchinator.table_widget import TableWidget
        self.resultTable = TableWidget(parent, "Execute", self.sendSqlClicked)
        
        return self.resultTable
    
    def add_menu(self,menu):
        pass

