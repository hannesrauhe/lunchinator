from PyQt4.QtCore import Qt, QVariant, QSize, pyqtSlot, QStringList, QMutex
from PyQt4.QtGui import QStandardItemModel, QStandardItem, QColor
import time
from lunchinator import log_exception

class TableModelBase(QStandardItemModel):
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
        item.setData(QSize(0, 20), Qt.SizeHintRole)
        return item
    
    def updateItem(self, key, data, row, column):
        item = self.item(row, column)
        if item != None:
            self.callItemInitializer(column, key, data, item)
        else:
            # item not initialized yet
            self.setItem(row, column, self.createItem(key, data, column))

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
                   ("LastSeen", self._updateLastSeenItem),
                   ("SendTo", self._updateSendToItem)]
        super(MembersTableModel, self).__init__(dataSource, columns)
        
        self.ipColIndex = 0
        self.nameColIndex = 1
        self.lunchTimeColIndex = 2
        self.lastSeenColIndex = 3
        self.sendToColIndex = 4
        
        self.nameKey= u'name'
        self.lunchBeginKey = u"next_lunch_begin"
        self.lunchEndKey = u"next_lunch_end"
        
        self.dontSendTo = set()
        
        # Called before server is running, no need to lock here
        infoDicts = self.dataSource.get_member_info()
        for ip in self.dataSource.get_members():
            infoDict = None
            if ip in infoDicts:
                infoDict = infoDicts[ip]
            self.appendContentRow(ip, infoDict)
            
        self.itemChanged.connect(self.itemChangedSlot)

    def _updateIpItem(self, ip, _, item):
        item.setText(ip)

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
        item.setData(QVariant(not ip in self.dontSendTo), Qt.DisplayRole)
        item.setEditable(True)
        
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateTimeouts(self):
        self.updateColumn(self.lastSeenColIndex)

    def itemChangedSlot(self, item):
        row = item.index().row()
        column = item.index().column()
        if column == self.sendToColIndex:
            ip = self.keys[row]
            sendTo = item.data(Qt.DisplayRole).toBool()
            if sendTo and ip in self.dontSendTo:
                self.dontSendTo.remove(ip)
            elif not sendTo and ip not in self.dontSendTo:
                self.dontSendTo.add(ip)

class ExtendedMembersModel(TableModelBase):
    def __init__(self, dataSource):
        super(ExtendedMembersModel, self).__init__(dataSource, None)
        self.headerNames = []
        self.mutex = QMutex()
        self.updateModel(self.dataSource.get_member_info())
    
    """ may be called concurrently """
    @pyqtSlot(dict)
    def updateModel(self, member_info, update = False, prepend = False):
        table_data = {"ip":[""]*len(member_info)}
        index = 0
        for ip,infodict in member_info.iteritems():
            table_data["ip"][index] = ip
            for k,v in infodict.iteritems():
                if not table_data.has_key(k):
                    table_data[k]=[""]*len(member_info)
                if False:#k=="avatar" and os.path.isfile(get_settings().get_avatar_dir()+"/"+v):
                    # TODO add avatar image
                    table_data[k][index]="avatars/%s"%v
                else:
                    table_data[k][index]=v
            index+=1
        
        # update columns labels
        for aHeaderName in table_data:
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
        self.updateModel({key: data})
        
    def externalRowPrepended(self, key, data):
        self.updateModel({key: data}, prepend=True)
    
    def externalRowUpdated(self, key, data):
        self.updateModel({key: data}, update=True)
    
    def externalRowRemoved(self, key):
        if key in self.keys:
            self.removeRow(self.keys.index(key))

class MessagesTableModel(TableModelBase):
    def __init__(self, dataSource):
        columns = [("Time", self._updateTimeItem),
                   ("Sender", self._updateSenderItem),
                   ("Message", self._updateMessageItem)]
        super(MessagesTableModel, self).__init__(dataSource, columns)
        
        # called before server is running, no need to lock here
        for aMsg in self.dataSource.getMessages():
            self.appendContentRow(aMsg[0], [aMsg[1], aMsg[2]])
            
    def _updateTimeItem(self, mTime, _, item):
        item.setText(time.strftime("%d.%m.%Y %H:%M:%S", mTime))
    
    def _updateSenderItem(self, _, m, item):
        item.setText(self.dataSource.memberName(m[0]))
    
    def _updateMessageItem(self, _, m, item):
        item.setText(m[1])
    
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
