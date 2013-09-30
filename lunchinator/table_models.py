from PyQt4.QtCore import Qt, QVariant, QStringList, QSize
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time

class TableModelBase(QStandardItemModel):
    def __init__(self, dataSource, columns):
        super(TableModelBase, self).__init__()
        self.dataSource = dataSource
        self.columns = columns
        self.setColumnCount(len(self.columns))
        
        stringList = QStringList()
        for colName, _ in self.columns:
            stringList.append(colName)
        self.setHorizontalHeaderLabels(stringList)

        for key in self.keys():
            self.appendContentRow(key)
        
    def createItem(self, key, column):
        item = QStandardItem()
        item.setEditable(False)
        self.columns[column][1](key, item)
        item.setData(QSize(0, 20), Qt.SizeHintRole)
        return item
    
    def updateItem(self, key, row, column):
        item = self.item(row, column)
        if item != None:
            self.columns[column][1](key, item)

    def createRow(self, key):
        row = []
        for column in range(self.columnCount()):
            row.append(self.createItem(key, column))
        return row

    def appendContentRow(self, key):
        self.appendRow(self.createRow(key))
        
    def prependContentRow(self, key):
        self.insertRow(0, self.createRow(key))
    
    def externalRowAppended(self):
        self.appendContentRow(self.keys()[-1])
        
    def externalRowPrepended(self):
        self.prependContentRow(self.keys()[0])
    
    def externalRowUpdated(self, index):
        self.updateRow(index)
    
    def externalRowRemoved(self, index):
        self.removeRow(index)

    def updateItemNoKey(self, row, column):
        key = self.keys()[row]
        self.updateItem(key, row, column)
        
    def updateColumn(self, column):
        keys = self.keys()
        for row, key in enumerate(keys):
            self.updateItem(key, row, column)
            
    def updateRow(self, row):
        key = self.keys()[row]
        for column in range(self.columnCount()):
            self.updateItem(key, row, column)

class MembersTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("IP", self._updateIpItem),
                   ("Name", self._updateNameItem),
                   ("LunchTime", self._updateLunchTimeItem),
                   ("LastSeen", self._updateLastSeenItem)]
        super(MembersTableModel, self).__init__(dataSource, columns)
        
        self.ipColIndex = 0
        self.nameColIndex = 1
        self.lunchTimeColIndex = 2
        self.lastSeenColIndex = 3

    def _updateIpItem(self, ip, item):
        item.setText(ip)

    def _updateNameItem(self, ip, item):
        infoDict = self.dataSource.get_member_info()
        if ip in infoDict and 'name' in infoDict[ip]:
            item.setText(infoDict[ip]['name'])
        else:
            item.setText(ip)
        
    def _updateLunchTimeItem(self, ip, item):
        infoDict = self.dataSource.get_member_info()
        if ip in infoDict and "next_lunch_begin" in infoDict[ip] and "next_lunch_end" in infoDict[ip]:
            item.setText(infoDict[ip]["next_lunch_begin"]+"-"+infoDict[ip]["next_lunch_end"])
            if self.dataSource.is_now_in_time_span(infoDict[ip]["next_lunch_begin"],infoDict[ip]["next_lunch_end"]):
                item.setData(QColor(0, 255, 0), Qt.DecorationRole)
            else:
                item.setData(QColor(255, 0, 0), Qt.DecorationRole)
        
        
    def _updateLastSeenItem(self, ip, item):
        intValue = -1
        if ip in self.dataSource.get_member_timeout():
            intValue = int(time.time()-self.dataSource.get_member_timeout()[ip])
        item.setData(QVariant(intValue), Qt.DisplayRole)
        return item
        
    def keys(self):
        return self.dataSource.get_members()
    
    def updateTimeouts(self):
        self.updateColumn(self.lastSeenColIndex)
            
    def updateIpItem(self, ip, row):
        self.updateItem(ip, row, self.ipColIndex)
    def updateNameItem(self, ip, row):
        self.updateItem(ip, row, self.nameColIndex)
    def updateLunchTimeItem(self, ip, row):
        self.updateItem(ip, row, self.lunchTimeColIndex)
    def updateLastSeenItem(self, ip, row):
        self.updateItem(ip, row, self.lastSeenColIndex)

class MessagesTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("Time", self._updateTimeItem),
                   ("Sender", self._updateSenderItem),
                   ("Message", self._updateMessageItem)]
        super(MessagesTableModel, self).__init__(dataSource, columns)
            
    def _updateTimeItem(self, m, item):
        item.setText(time.strftime("%d.%m.%Y %H:%M:%S", m[0]))
    
    def _updateSenderItem(self, m, item):
        item.setText(self.dataSource.memberName(m[1]))
    
    def _updateMessageItem(self, m, item):
        item.setText(m[2])
        
    def updateSenders(self, _ = None):
        self.updateColumn(1)
    
    def keys(self):
        return self.dataSource.get_last_msgs()
