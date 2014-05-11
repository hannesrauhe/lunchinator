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

class MembersTableModel(TableModelBase):
    LUNCH_TIME_TIMER_ROLE = TableModelBase.SORT_ROLE + 1
    _NAME_KEY = u'name'
    _GROUP_KEY = u"group"
    _LUNCH_BEGIN_KEY = u"next_lunch_begin"
    _LUNCH_END_KEY = u"next_lunch_end"
    
    NAME_COL_INDEX = 0
    GROUP_COL_INDEX = 1
    LUNCH_TIME_COL_INDEX = 2
    SEND_TO_COL_INDEX = 3
    
    def __init__(self, dataSource):
        columns = [(u"Name", self._updateNameItem),
                   (u"Group", self._updateGroupItem),
                   (u"LunchTime", self._updateLunchTimeItem)]
        super(MembersTableModel, self).__init__(dataSource, columns)
        
        # Called before server is running, no need to lock here
        for peerID in self.dataSource:
            infoDict = dataSource.getPeerInfo(peerID)
            self.appendContentRow(peerID, infoDict)
            
    def _getRowToolTip(self, peerID, _infoDict):
        return u"ID: %s\nIPs: %s" % (peerID, ', '.join(get_peers().getPeerIPs(peerID)))

    def _updateIpItem(self, ip, _, item):
        item.setData(QVariant(ip), Qt.DisplayRole)

    def _updateNameItem(self, ip, infoDict, item):
        if self._NAME_KEY in infoDict:
            item.setText(infoDict[self._NAME_KEY])
        else:
            item.setText(ip)
        
    def removeRow(self, row, parent=QModelIndex()):
        # ensure no timer is active after a row has been removed
        item = self.item(row, self.LUNCH_TIME_COL_INDEX)
        timer = item.data(self.LUNCH_TIME_TIMER_ROLE)
        if timer != None:
            timer.stop()
            timer.deleteLater()
        return TableModelBase.removeRow(self, row, parent)
        
    def _updateLunchTimeItem(self, ip, infoDict, item):
        oldTimer = item.data(self.LUNCH_TIME_TIMER_ROLE)
        if oldTimer != None:
            oldTimer.stop()
            oldTimer.deleteLater()
        if self._LUNCH_BEGIN_KEY in infoDict and self._LUNCH_END_KEY in infoDict:
            item.setText(infoDict[self._LUNCH_BEGIN_KEY]+"-"+infoDict[self._LUNCH_END_KEY])
            try:
                beginTime = datetime.strptime(infoDict[self._LUNCH_BEGIN_KEY], lunch_settings.LUNCH_TIME_FORMAT)
                beginTime = beginTime.replace(year=2000)
                item.setData(QVariant(time.mktime(beginTime.timetuple())), self.SORT_ROLE)
                timeDifference = getTimeDifference(infoDict[self._LUNCH_BEGIN_KEY],infoDict[self._LUNCH_END_KEY])
                if timeDifference != None:
                    if timeDifference > 0:
                        item.setData(QColor(0, 255, 0), Qt.DecorationRole)
                    else:
                        item.setData(QColor(255, 0, 0), Qt.DecorationRole)
                    
                    if timeDifference != 0:
                        timer = QTimer(item.model())
                        timer.timeout.connect(partial(self._updateLunchTimeItem, ip, infoDict, item))
                        timer.setSingleShot(True)
                        timer.start(abs(timeDifference))
            except ValueError:
                log_debug("Ignoring illegal lunch time:", infoDict[self._LUNCH_BEGIN_KEY])
        else:
            item.setData(QVariant(-1), self.SORT_ROLE)
            
    def _updateGroupItem(self, _peerID, infoDict, item):
        if self._GROUP_KEY in infoDict:
            item.setText(infoDict[self._GROUP_KEY])
        else:
            item.setText(u"")
        
    def _updateLastSeenItem(self, peerID, _, item):
        intValue = -1
        timeout = self.dataSource.getIDLastSeen(peerID)
        if timeout != None:
            intValue = int(time.time() - timeout)
        item.setData(QVariant(intValue), Qt.DisplayRole)
    
class ExtendedMembersModel(TableModelBase):
    def __init__(self, dataSource):
        super(ExtendedMembersModel, self).__init__(dataSource, None)
        self.headerNames = []
        self.mutex = QMutex()
        self.updateModel(self.dataSource.getPeerInfoDict())
    
    @pyqtSlot(dict)
    def updateModel(self, member_info, update=False, prepend=False):
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
    
    """ may be called concurrently """
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

class MessagesTableModelOld(TableModelBase):
    def __init__(self, dataSource):
        columns = [("Time", self._updateTimeItem),
                   ("Sender", self._updateSenderItem),
                   ("Message", self._updateMessageItem)]
        super(MessagesTableModelOld, self).__init__(dataSource, columns)
        
        self.setSortRole(self.SORT_ROLE)
        # called before server is running, no need to lock here
        for aMsg in self.dataSource.getAll():
            self.appendContentRow(aMsg[0], [aMsg[1], aMsg[2]])
            
    def _updateTimeItem(self, mTime, _, item):
        item.setData(QVariant(time.strftime("%d.%m.%Y %H:%M:%S", mTime)), Qt.DisplayRole)
        item.setData(QVariant(time.mktime(mTime)), self.SORT_ROLE)
    
    def _updateSenderItem(self, _, m, item):
        peerID = convert_string(m[0])
        name = get_peers().getPeerNameNoLock(peerID)
        if not name:
            # check if peerID is IP (from old version)
            peerID = get_peers().getPeerIDNoLock(peerID)
            if peerID:
                name = get_peers().getPeerNameNoLock(peerID)
        data = QVariant(get_peers().getPeerNameNoLock(peerID))
        item.setData(data, Qt.DisplayRole)
    
    def _updateMessageItem(self, _, m, item):
        data = QVariant(m[1])
        item.setData(data, Qt.DisplayRole)
    
    """ --------------------- SLOTS ---------------------- """
    
    @pyqtSlot()
    def updateSenders(self):
        with get_peers():
            for row, aMsg in enumerate(self.dataSource.getAll()):
                self.updateItem(aMsg[0], [aMsg[1], aMsg[2]], row, 1)

class MessagesTableModel(QAbstractItemModel):
    SORT_ROLE = Qt.UserRole + 1
    
    def __init__(self, parent):
        super(MessagesTableModel, self).__init__(parent)
        self._messages = get_server().get_messages().getSlidingWindowCache(100)
        
    def index(self, row, column, _parent=QModelIndex()):
        if row < len(self._messages) and row >= 0 and column < 3 and column >= 0:
            return super(MessagesTableModel, self).createIndex(row, column)
        return QModelIndex()
    
    def parent(self, _child):
        return QModelIndex()
    
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() and parent.column() != 0 else len(self._messages)
    
    def columnCount(self, parent=None):
        return 0 if parent.isValid() else 3
    
    def _getMessage(self, row):
        return self._messages[len(self._messages) - 1 - row]
    
    def _formatTime(self, mTime):
        dt = datetime.fromtimestamp(mktime(mTime))
        if dt.date() == datetime.today().date():
            return time.strftime("Today %H:%M", mTime)
        elif dt.date() == (datetime.today() - timedelta(days=1)).date():
            return time.strftime("Yesterday %H:%M", mTime)
        elif dt.date().year == datetime.today().date().year:
            return time.strftime("%b %d, %H:%M", mTime)
        return time.strftime("%b %d %Y, %H:%M", mTime)
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            message = self._getMessage(index.row())
            if index.column() == 0:
                # time
                mTime = message[0]
                return QVariant(self._formatTime(mTime))
            elif index.column() == 1:
                # sender
                peerID = message[1]
                name = get_peers().getPeerNameNoLock(peerID)
                if not name:
                    # check if peerID is IP (from old version)
                    peerID = get_peers().getPeerIDNoLock(peerID)
                    if peerID:
                        name = get_peers().getPeerNameNoLock(peerID)
                return QVariant(get_peers().getPeerNameNoLock(peerID))
            else:
                return QVariant(message[2])
        elif role == Qt.SizeHintRole:
            return QSize(0, 20)
        elif role == self.SORT_ROLE:
            mTime = self._getMessage(index.row())[0]
            if index.column() == 0:
                return QVariant(time.mktime(mTime))
        return QVariant()
            
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if section == 0:
                return QVariant("Time")
            elif section == 1:
                return QVariant("Sender")
            elif section == 2:
                return QVariant("Message")
        return super(MessagesTableModel, self).headerData(section, orientation, role)
            
    def messagePrepended(self, _time, _sender, _message):
        self.rowsInserted.emit(QModelIndex(), 0, 0)

    def updateSenders(self):
        self.dataChanged.emit(self.createIndex(0, 1), self.createIndex(len(self._messages), 1))
