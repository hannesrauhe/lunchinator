from lunchinator.iface_plugins import iface_gui_plugin, db_for_plugin_iface
from lunchinator import log_exception, log_error, get_settings, get_server, get_db_connection
import urllib2,sys

    
class sql_interface(iface_gui_plugin):
    def __init__(self):
        super(sql_interface, self).__init__()
        self.sqlResultTable = None
        self.times_called=0
        self.last_key=-1
        self.options = [((u"query_db_connection", u"DB Connection to send statements to", 
                          get_settings().get_available_db_connections()),
                         get_settings().get_default_db_connection()),
                        ((u"db_connection", u"DB Connection to store history", 
                          get_settings().get_available_db_connections(),
                          self.connect_to_db),
                         get_settings().get_default_db_connection()),
                        ((u"use_textedit", u"Use multi-line sql editor"),False)]
        self.db_connection = None
        
        self.add_supported_dbms("SQLite Connection", sql_commands_sqlite)
    
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
        
        self.specialized_db_conn().insert_command(sql_stat)
        
        if None==self.db_connection:        
            self.db_connection, _ = get_db_connection(self.options["query_db_connection"])
                    
        try:
            header, res = self.db_connection.queryWithHeader(sql_stat)
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

class sql_commands_sqlite(db_for_plugin_iface):
    def init_db(self):
        if not self.get_db_conn().existsTable("SQL_INTERFACE_HISTORY"):
            self.get_db_conn().execute("CREATE TABLE SQL_INTERFACE_COMMANDS(cmd_id INTEGER PRIMARY KEY AUTOINCREMENT, CMD TEXT) ")

    def insert_command(self, cmd):
        self.get_db_conn().execute("INSERT INTO SQL_INTERFACE_HISTORY(CMD) VALUES(?)",cmd)