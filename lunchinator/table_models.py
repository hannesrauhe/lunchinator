from PyQt4.QtCore import Qt, QVariant, QSize, pyqtSlot, QStringList, QMutex, QString, QTimer, QModelIndex,\
    QAbstractItemModel
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time
from functools import partial
from datetime import datetime, timedelta
from lunchinator import convert_string, get_peers, log_debug,\
    get_server
from lunch_settings import lunch_settings
from lunchinator.utilities import getTimeDifference
from time import mktime

class TableModelBase(QStandardItemModel):
    KEY_ROLE = Qt.UserRole + 1
    SORT_ROLE = Qt.UserRole + 2
    
    def __init__(self, dataSource, columns):
        super(TableModelBase, self).__init__()
        self.dataSource = dataSource
        self.columns = columns
        if self.columns != None:
            self.setColumnCount(len(self.columns))
            stringList = QStringList()
            for colName, _ in self.columns:
                stringList.append(colName)
            self.setHorizontalHeaderLabels(stringList)
        self.keys = []

    def hasKey(self, key):
        return key in self.keys

    def callItemInitializer(self, column, key, data, item):
        item.setData(None, self.SORT_ROLE)
        self.columns[column][1](key, data, item)

    def createItem(self, key, data, column):
        item = QStandardItem()
        item.setEditable(False)
        self.callItemInitializer(column, key, data, item)
        if item.data(self.SORT_ROLE) == None:
            item.setData(item.data(Qt.DisplayRole), self.SORT_ROLE)
        item.setData(key, self.KEY_ROLE)
        item.setData(QSize(0, 20), Qt.SizeHintRole)
        return item
    
    def updateItem(self, key, data, row, column):
        item = self.item(row, column)
        if item != None:
            self.callItemInitializer(column, key, data, item)
        else:
            # item not initialized yet
            item = self.createItem(key, data, column)
            self.setItem(row, column, item)
        if item.data(self.SORT_ROLE) == None:
            item.setData(item.data(Qt.DisplayRole), self.SORT_ROLE)

    def _updateToolTips(self, row, key, data):
        toolTipText = self._getRowToolTip(key, data)
        if toolTipText:
            toolTip = QVariant(toolTipText)
        else:
            toolTip = None
        for item in row:
            if item.data(Qt.ToolTipRole) == None:
                item.setData(toolTip, Qt.ToolTipRole)
            
    def createRow(self, key, data):
        row = []
        for column in range(self.columnCount()):
            row.append(self.createItem(key, data, column))
        self._updateToolTips(row, key, data)
        return row
    
    def insertContentRow(self, key, data, index):
        self.keys.insert(index, key)
        self.insertRow(index, self.createRow(key, data))
        
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
        self._updateToolTips((self.item(row, colIndex) for colIndex in xrange(self.columnCount())), key, data)
            
    @classmethod   
    def convertDict(cls, aDict):
        newDict = {}
        for aKey in aDict:
            newKey = aKey
            if type(aKey) == QString:
                newKey = convert_string(aKey)
            aValue = aDict[aKey]
            if type(aValue) == QString:
                aValue = convert_string(aValue)
            elif type(aValue) == QVariant:
                aValue = convert_string(aValue.toString())
            newDict[newKey] = aValue
        return newDict
            
    def _checkDict(self, data):
        if type(data) == dict:
            for aKey in data:
                if type(aKey) == QString:
                    return self.convertDict(data)
                if type(data[aKey]) == QString:
                    return self.convertDict(data)
        return data
                    
    """ --------- IMPLEMENT IN SUBCLASS ----------- """
    def _getRowToolTip(self, _key, _data):
        """Returns the tool tip to display on the whole row.
        
        Use this method if the model does not add tool tips to specific
        items. This method will be called once for each row, on creation
        and on each update. If an item already has tool tip data, it
        won't be overwritten.
        """
        return None
    
    """ ----------------- SLOTS ------------------- """
            
    def externalRowInserted(self, key, data, index):
        if type(key) == QString:
            key = convert_string(key)
        data = self._checkDict(data)
        self.insertContentRow(key, data, index)
        
    def externalRowAppended(self, key, data):
        if type(key) == QString:
            key = convert_string(key)
        data = self._checkDict(data)
        self.appendContentRow(key, data)
        
    def externalRowPrepended(self, key, data):
        if type(key) == QString:
            key = convert_string(key)
        data = self._checkDict(data)
        self.prependContentRow(key, data)
    
    def externalRowUpdated(self, key, data):
        if type(key) == QString:
            key = convert_string(key)
        data = self._checkDict(data)
        if key in self.keys:
            index = self.keys.index(key)
            self.updateRow(key, data, index)
    
    def externalRowRemoved(self, key):
        if type(key) == QString:
            key = convert_string(key)
        if key in self.keys:
            index = self.keys.index(key)
            del self.keys[index]
            self.removeRow(index)
