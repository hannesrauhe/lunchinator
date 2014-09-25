from lunchinator.plugin import iface_gui_plugin, db_for_plugin_iface
from lunchinator import get_settings, get_server, get_db_connection
import sys
from lunchinator.cli import LunchCLIModule
from PyQt4.QtCore import Qt, QVariant

    
class sql_interface(iface_gui_plugin, LunchCLIModule):
    def __init__(self):
        LunchCLIModule.__init__(self)
        iface_gui_plugin.__init__(self)
        
        self.sqlResultTable = None
        self.times_called=0
        self.last_key=-1
        self.options = [((u"query_db_connection", u"DB Connection to send statements to", [],
                          self._changeQueryDB),
                         get_settings().get_default_db_connection()),
                        ((u"db_connection", u"DB Connection to store history", [],
                          self._reconnectDB),
                         get_settings().get_default_db_connection()),
                        ((u"use_textedit", u"Use multi-line sql editor"),False)]
        self.db_connection = None
        
        self.add_supported_dbms("SQLite Connection", sql_commands_sqlite)
    
    def _getChoiceOptions(self, o):
        if o == u"query_db_connection":
            return get_settings().get_available_db_connections()
        elif o == u"db_connection":
            return self.get_supported_connections()
        return super(sql_interface, self)._getChoiceOptions(o)
    
    def _changeQueryDB(self, _set, _newVal):
        self.db_connection = None
    
    def _reconnectDB(self, setting, newVal):
        self.reconnect_db(setting, newVal)
        self.resultTable.clearHistory()
        hist = self.specialized_db_conn().get_last_commands()
        if hist:
            self.resultTable.addToHistory(hist)
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)        
    
    def do_SQL(self, cmd):
        if None==self.db_connection:
            self.db_connection, _ = get_db_connection(self.logger, self.options["query_db_connection"])
        try:
            header, res = self.db_connection.queryWithHeader(cmd)
            self.appendOutput(*header)
            self.appendSeparator()
            for r in res:
                self.appendOutput(*r)
            self.flushOutput()
        except Exception as e:
            print "Error in SQL statement",str(e)
        
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
#             self.logger.warning("SQL error:")
            return False
        
        columns = []
        for h in header:
            columns.append((h,self.empty))
        mod = TableModelBase(None, columns, self.logger)
        self.times_called = 0
        for i,r in enumerate(res):
            mod.appendContentRow(i, r)
            if i>1000:
                break
        self.resultTable.setModel(mod)
        for c in xrange(mod.columnCount()):
            self.resultTable.getTable().resizeColumnToContents(c)
        return True
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
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