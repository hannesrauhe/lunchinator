from PyQt4.QtCore import Qt, QVariant, QSize, pyqtSlot, QStringList, QMutex, QString
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time,datetime
from lunchinator import log_exception, convert_string, log_error, log_warning,\
    get_server, get_settings

class TableModelBase(QStandardItemModel):
    SORT_ROLE = Qt.UserRole
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

    def callItemInitializer(self, column, key, data, item):
        self.columns[column][1](key, data, item)

    def createItem(self, key, data, column):
        item = QStandardItem()
        item.setEditable(False)
        self.callItemInitializer(column, key, data, item)
        if item.data(self.SORT_ROLE) == None:
            item.setData(item.data(Qt.DisplayRole), self.SORT_ROLE)
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
            
    def _convertDict(self, aDict):
        newDict = {}
        for aKey in aDict:
            if type(aKey) == QString:
                aKey = convert_string(aKey)
            aValue = aDict[aKey]
            if type(aValue) == QString:
                aValue = convert_string(aValue)
            newDict[aKey] = aValue
        return newDict
            
    def _checkDict(self, data):
        if type(data) == dict:
            for aKey in data:
                if type(aKey) == QString:
                    log_warning("encountered QString as key of dict", data)
                    return self._convertDict(data)
                if type(data[aKey]) == QString:
                    log_warning("encountered QString as value of dict", data)
                    return self._convertDict(data)
        return data
                    
    """ ----------------- SLOTS ------------------- """
            
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
            self.removeRow(self.keys.index(key))

class MembersTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("IP", self._updateIpItem),
                   ("Name", self._updateNameItem),
                   ("LunchTime", self._updateLunchTimeItem),
                   ("LastSeen", self._updateLastSeenItem)]
        if get_settings().get_advanced_gui_enabled():
            columns.append(("SendTo", self._updateSendToItem))
        super(MembersTableModel, self).__init__(dataSource, columns)
        
        self.ipColIndex = 0
        self.nameColIndex = 1
        self.lunchTimeColIndex = 2
        self.lastSeenColIndex = 3
        self.sendToColIndex = 4
        
        self.nameKey= u'name'
        self.lunchBeginKey = u"next_lunch_begin"
        self.lunchEndKey = u"next_lunch_end"
        
        # Called before server is running, no need to lock here
        infoDicts = self.dataSource.get_member_info()
        for ip in self.dataSource.get_members():
            infoDict = None
            if ip in infoDicts:
                infoDict = infoDicts[ip]
            self.appendContentRow(ip, infoDict)
            
        self.itemChanged.connect(self.itemChangedSlot)

    def _updateIpItem(self, ip, _, item):
        item.setData(QVariant(ip), Qt.DisplayRole)

    def _updateNameItem(self, ip, infoDict, item):
        if self.nameKey in infoDict:
            item.setText(infoDict[self.nameKey])
        else:
            item.setText(ip)
        
    def is_now_in_time_span(self,begin,end):
        try:
            beginList = begin.split(":")
            endList = end.split(":")
            return time.localtime()[3]*60+time.localtime()[4] >= int(str(beginList[0]))*60+int(str(beginList[1])) and time.localtime()[3]*60+time.localtime()[4] <= int(str(endList[0]))*60+int(str(endList[1]))
        except:
            log_exception("don't know how to handle time span")
            return False;
        
    def _updateLunchTimeItem(self, _, infoDict, item):
        if self.lunchBeginKey in infoDict and self.lunchEndKey in infoDict:
            item.setText(infoDict[self.lunchBeginKey]+"-"+infoDict[self.lunchEndKey])
            beginTime = datetime.datetime.strptime(infoDict[self.lunchBeginKey], "%H:%M")
            beginTime = beginTime.replace(year=2000)
            item.setData(QVariant(time.mktime(beginTime.timetuple())), self.SORT_ROLE)
            if self.is_now_in_time_span(infoDict[self.lunchBeginKey],infoDict[self.lunchEndKey]):
                item.setData(QColor(0, 255, 0), Qt.DecorationRole)
            else:
                item.setData(QColor(255, 0, 0), Qt.DecorationRole)
        
    def _updateLastSeenItem(self, ip, _, item):
        intValue = -1
        if ip in self.dataSource.get_member_timeout():
            intValue = int(time.time()-self.dataSource.get_member_timeout()[ip])
        item.setData(QVariant(intValue), Qt.DisplayRole)
    
    def _updateSendToItem(self, ip, _, item):
        checkstate = Qt.Unchecked if ip in self.dataSource.dontSendTo else Qt.Checked
        item.setCheckState(checkstate)
        item.setCheckable(True)
        
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateTimeouts(self):
        self.updateColumn(self.lastSeenColIndex)

    def itemChangedSlot(self, item):
        row = item.index().row()
        column = item.index().column()
        if column == self.sendToColIndex:
            ip = self.keys[row]
            sendTo = item.checkState() == Qt.Checked
            if sendTo and ip in self.dataSource.dontSendTo:
                self.dataSource.dontSendTo.remove(ip)
            elif not sendTo and ip not in self.dataSource.dontSendTo:
                self.dataSource.dontSendTo.add(ip)

class ExtendedMembersModel(TableModelBase):
    def __init__(self, dataSource):
        super(ExtendedMembersModel, self).__init__(dataSource, None)
        self.headerNames = []
        self.mutex = QMutex()
        self.updateModel(self.dataSource.get_member_info())
    
    """ may be called concurrently """
    @pyqtSlot(dict)
    def updateModel(self, member_info, update = False, prepend = False):
        table_headers = set()
        table_headers.add(u"ip") 
        for infodict in member_info.itervalues():
            for k in infodict:
                if not k in table_headers:
                    table_headers.add(convert_string(k))
        
        # update columns labels
        for aHeaderName in table_headers:
            if not aHeaderName in self.headerNames:
                self.setHorizontalHeaderItem(len(self.headerNames), QStandardItem(aHeaderName))
                self.headerNames.append(aHeaderName)

        for ip in member_info:
            if update:
                if ip in self.keys:
                    index = self.keys.index(ip)
                    self.updateRow(ip, member_info[ip], index)
            elif prepend:
                self.prependContentRow(ip, member_info[ip])
            else:
                self.appendContentRow(ip, member_info[ip])
    
    def callItemInitializer(self, column, key, data, item):
        headerName = self.headerNames[column]
        text = ""
        if headerName == "ip":
            text = key
        elif headerName in data:
            text = data[headerName]
        item.setData(QVariant(text), Qt.DisplayRole)
        
    def externalRowAppended(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel({key: data})
        
    def externalRowPrepended(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel({key: data}, prepend=True)
    
    def externalRowUpdated(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel({key: data}, update=True)
    
    def externalRowRemoved(self, key):
        key = convert_string(key)
        if key in self.keys:
            self.removeRow(self.keys.index(key))

class MessagesTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("Time", self._updateTimeItem),
                   ("Sender", self._updateSenderItem),
                   ("Message", self._updateMessageItem)]
        super(MessagesTableModel, self).__init__(dataSource, columns)
        
        self.setSortRole(self.SORT_ROLE)
        # called before server is running, no need to lock here
        for aMsg in self.dataSource.getMessages():
            self.appendContentRow(aMsg[0], [aMsg[1], aMsg[2]])
            
    def _updateTimeItem(self, mTime, _, item):
        item.setData(QVariant(time.strftime("%d.%m.%Y %H:%M:%S", mTime)), Qt.DisplayRole)
        item.setData(QVariant(time.mktime(mTime)), self.SORT_ROLE)
    
    def _updateSenderItem(self, _, m, item):
        data = QVariant(self.dataSource.memberName(m[0]))
        item.setData(data, Qt.DisplayRole)
    
    def _updateMessageItem(self, _, m, item):
        data = QVariant(m[1])
        item.setData(data, Qt.DisplayRole)
    
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateSenders(self):
        self.dataSource.lockMembers()
        try:
            self.dataSource.lockMessages()
            try:
                for row, aMsg in enumerate(self.dataSource.getMessages()):
                    self.updateItem(aMsg[0], [aMsg[1], aMsg[2]], row, 1)
            finally:
                self.dataSource.releaseMessages()
        finally:
            self.dataSource.releaseMembers()
