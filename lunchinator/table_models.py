from PyQt4.QtCore import Qt, QVariant, QStringList, QSize, pyqtSlot
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time
from lunchinator import get_server

class TableModelBase(QStandardItemModel):
    def __init__(self, dataSource, columns):
        super(TableModelBase, self).__init__()
        self.dataSource = dataSource
        self.columns = columns
        self.setColumnCount(len(self.columns))
        self.keys = []
        
        stringList = QStringList()
        for colName, _ in self.columns:
            stringList.append(colName)
        self.setHorizontalHeaderLabels(stringList)

    def createItem(self, key, data, column):
        item = QStandardItem()
        item.setEditable(False)
        self.columns[column][1](key, data, item)
        item.setData(QSize(0, 20), Qt.SizeHintRole)
        return item
    
    def updateItem(self, key, data, row, column):
        item = self.item(row, column)
        if item != None:
            self.columns[column][1](key, data, item)

    def createRow(self, key, data):
        row = []
        for column in range(self.columnCount()):
            row.append(self.createItem(key, data, column))
        return row

    def appendContentRow(self, key, data):
        self.keys.append(key)
        self.appendRow(self.createRow(key, data))
        
    def prependContentRow(self, key, data):
        self.keys.insert(0, key)
        self.insertRow(0, self.createRow(key, data))

    def updateColumn(self, column):
        for row, key in enumerate(self.keys):
            self.updateItem(key, None, row, column)
            
    def updateRow(self, key, data, row):
        for column in range(self.columnCount()):
            self.updateItem(key, data, row, column)
            
    """ ----------------- SLOTS ------------------- """
            
    def externalRowAppended(self, key, data):
        self.appendContentRow(key, data)
        
    def externalRowPrepended(self, key, data):
        self.prependContentRow(key, data)
    
    def externalRowUpdated(self, key, data):
        if key in self.keys:
            index = self.keys.index(key)
            self.updateRow(key, data, index)
    
    def externalRowRemoved(self, key):
        if key in self.keys:
            self.removeRow(self.keys.index(key))

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
        
        infoDicts = get_server().get_member_info()
        for ip in get_server().get_members():
            infoDict = None
            if ip in infoDicts:
                infoDict = infoDicts[ip]
            self.appendContentRow(ip, infoDict)

    def _updateIpItem(self, ip, _, item):
        item.setText(ip)

    def _updateNameItem(self, ip, infoDict, item):
        if 'name' in infoDict:
            item.setText(infoDict['name'])
        else:
            item.setText(ip)
        
    def _updateLunchTimeItem(self, _, infoDict, item):
        if "next_lunch_begin" in infoDict and "next_lunch_end" in infoDict:
            item.setText(infoDict["next_lunch_begin"]+"-"+infoDict["next_lunch_end"])
            if self.dataSource.is_now_in_time_span(infoDict["next_lunch_begin"],infoDict["next_lunch_end"]):
                item.setData(QColor(0, 255, 0), Qt.DecorationRole)
            else:
                item.setData(QColor(255, 0, 0), Qt.DecorationRole)
        
        
    def _updateLastSeenItem(self, ip, _, item):
        intValue = -1
        if ip in self.dataSource.get_member_timeout():
            intValue = int(time.time()-self.dataSource.get_member_timeout()[ip])
        item.setData(QVariant(intValue), Qt.DisplayRole)
        return item
        
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateTimeouts(self):
        self.updateColumn(self.lastSeenColIndex)

class MessagesTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("Time", self._updateTimeItem),
                   ("Sender", self._updateSenderItem),
                   ("Message", self._updateMessageItem)]
        super(MessagesTableModel, self).__init__(dataSource, columns)
        
        get_server().lockMessages()
        try:
            for aMsg in get_server().getMessages():
                self.appendContentRow(aMsg[0], [aMsg[1], aMsg[2]])
        finally:
            get_server().releaseMessages()
            
    def _updateTimeItem(self, mTime, _, item):
        item.setText(time.strftime("%d.%m.%Y %H:%M:%S", mTime))
    
    def _updateSenderItem(self, _, m, item):
        item.setText(self.dataSource.memberName(m[0]))
    
    def _updateMessageItem(self, _, m, item):
        item.setText(m[1])
        
    def initialKeys(self):
        return get_server().get_members()
    
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateSenders(self):
        get_server().lockMessages()
        try:
            for row, aMsg in enumerate(get_server().getMessages()):
                self.updateItem(aMsg[0], [aMsg[1], aMsg[2]], row, 1)
        finally:
            get_server().releaseMessages()
