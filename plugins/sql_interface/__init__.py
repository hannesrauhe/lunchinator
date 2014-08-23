from lunchinator.plugin import iface_gui_plugin, db_for_plugin_iface
from lunchinator import get_settings, get_server, get_db_connection
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
                          self.reconnect_db),
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
        item.setText(unicode(data[self.times_called]))
        self.times_called+=1
        
    def sendSqlClicked(self, sql_stat):
        from PyQt4.QtGui import QMessageBox
        from lunchinator.table_models import TableModelBase
        
        self.specialized_db_conn().insert_command(sql_stat)
        
        if None==self.db_connection:        
            self.db_connection, _ = get_db_connection(self.logger, self.options["query_db_connection"])
                    
        try:
            header, res = self.db_connection.queryWithHeader(sql_stat)
        except Exception as e:
            QMessageBox.warning(self.resultTable,"Error in SQL statement",str(e))
            self.logger.error("SQL error:")
            return False
        
        columns = []
        for h in header:
            columns.append((h,self.empty))
        mod = TableModelBase(get_server(), columns, self.logger)
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
        hist = self.specialized_db_conn().get_last_commands()
        if hist:
            self.resultTable.addToHistory(hist)
        return self.resultTable
    
    def add_menu(self,menu):
        pass

class sql_commands_sqlite(db_for_plugin_iface):
    def init_db(self):
        if not self.get_db_conn().existsTable("SQL_INTERFACE_HISTORY"):
            self.get_db_conn().execute("CREATE TABLE SQL_INTERFACE_HISTORY(cmd_id INTEGER PRIMARY KEY AUTOINCREMENT, CMD TEXT) ")

    def insert_command(self, cmd):
        self.get_db_conn().execute("INSERT INTO SQL_INTERFACE_HISTORY(CMD) VALUES(?)",cmd)
        
    def get_last_commands(self, limit = 100):
        tmp = self.get_db_conn().query("SELECT CMD FROM SQL_INTERFACE_HISTORY ORDER BY cmd_id DESC LIMIT ?", limit)
        tmp.reverse()
        res = [c[0] for c in tmp]
        return res