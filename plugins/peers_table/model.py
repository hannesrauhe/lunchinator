from lunchinator import log_exception, convert_string, get_settings
from lunchinator.table_models import TableModelBase

from PyQt4.QtCore import Qt, QVariant, QSize, pyqtSlot, QStringList, QMutex, QString, QTimer, QModelIndex
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time

class PeersTableModel(TableModelBase):
    LUNCH_TIME_TIMER_ROLE = TableModelBase.SORT_ROLE + 1
    
    def __init__(self, dataSource):
        columns = [("IP", self._updateIpItem),
                   ("LastSeen", self._updateLastSeenItem)]
        super(PeersTableModel, self).__init__(dataSource, columns)
        
        self.ipColIndex = 0
        self.lastSeenColIndex = 1

    def _updateIpItem(self, ip, _, item):
        item.setData(QVariant(ip), Qt.DisplayRole)
        
    def removeRow(self, row, parent = QModelIndex()):
        # ensure no timer is active after a row has been removed
        item = self.item(row, self.lunchTimeColIndex)
        timer = item.data(self.LUNCH_TIME_TIMER_ROLE)
        if timer != None:
            timer.stop()
            timer.deleteLater()
        return TableModelBase.removeRow(self, row, parent)
        
    def _updateLastSeenItem(self, ip, _, item):
        intValue = -1
        if ip in self.dataSource.get_peer_timeout():
            intValue = int(time.time()-self.dataSource.get_peer_timeout()[ip])
        item.setData(QVariant(intValue), Qt.DisplayRole)
        
    
    def externalRowAppended(self, key):
        if type(key) == QString:
            key = convert_string(key)
        self.appendContentRow(key, None)
        
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateTimeouts(self):
        self.updateColumn(self.lastSeenColIndex)