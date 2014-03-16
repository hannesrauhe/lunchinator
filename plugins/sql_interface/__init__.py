from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, log_error, get_settings, get_server
import urllib2,sys
    
class sql_interface(iface_gui_plugin):
    def __init__(self):
        super(sql_interface, self).__init__()
        self.sqlResultTable = None
        self.times_called=0
        self.last_key=-1
        self.options = [((u"db_connection", u"DB Connection", [u'auto']),"auto"),
                        ((u"use_textedit", u"Use multi-line sql editor"),False)]
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)        
    
    def do_SQL(self, cmd):
        from lunchinator.cli import LunchCLIModule
        #l = LunchCLIModule()
        for r in self.query(cmd):
            print r
        #l.flushOutput()
        
    def empty(self,key,data,item):
        if key!=self.last_key:
            self.last_key=key
            self.times_called=0
        item.setText(str(data[self.times_called]))
        self.times_called+=1
        
    def sendSqlClicked(self, sql_stat):
        from PyQt4.QtGui import QMessageBox
        from lunchinator.table_models import TableModelBase
        try:
            header, res = get_server().getDBConnection(self.options['db_connection']).queryWithHeader(sql_stat)
        except Exception as e:
            QMessageBox.warning(self.resultTable,"Error in SQL statement",str(e))
            log_error("SQL error:")
            return False
        
        columns = []
        for h in header:
            columns.append((h,self.empty))
        mod = TableModelBase(get_server(), columns)
        for i,r in enumerate(res):
            mod.appendContentRow(i, r)
            if i>1000:
                break
        self.resultTable.setModel(mod)
        return True
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import Qt
        from lunchinator.table_widget import TableWidget
        self.resultTable = TableWidget(parent, "Execute", self.sendSqlClicked, useTextEdit=self.options['use_textedit'])
        
        return self.resultTable
    
    def add_menu(self,menu):
        pass

