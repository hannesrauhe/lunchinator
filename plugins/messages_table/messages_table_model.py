from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QVariant, QSize
from lunchinator import get_server, get_peers
import time
from lunchinator.utilities import formatTime
from lunchinator.log.logging_slot import loggingSlot

class MessagesTableModel(QAbstractItemModel):
    SORT_ROLE = Qt.UserRole + 1
    
    TIME_COL = 0
    SENDER_COL = 1
    MESSAGE_COL = 2
    
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
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            message = self._getMessage(index.row())
            if index.column() == self.TIME_COL:
                # time
                mTime = message[0]
                return QVariant(formatTime(mTime))
            elif index.column() == self.SENDER_COL:
                # sender
                peerID = message[1]
                # look in peers first, it's always up to date
                name = get_peers().getDisplayedPeerName(pID=peerID, lock=False)
                if not name:
                    # look up in stored peer names
                    name = get_peers().getDisplayedPeerName(pID=peerID) 
                    if not name:
                        # check if peerID is IP (from old version)
                        name = get_peers().getDisplayedPeerName(pIP=peerID, lock=False)
                        if not name:
                            name = peerID
                return QVariant(name)
            else:
                return QVariant(message[2])
        elif role == Qt.SizeHintRole:
            return QSize(0, 20)
        elif role == self.SORT_ROLE:
            if index.column() == self.TIME_COL:
                mTime = self._getMessage(index.row())[0]
                return QVariant(time.mktime(mTime))
            else:
                # return display role as fallback
                return self.data(index)
        elif role == Qt.ToolTipRole:
            if index.column() == self.MESSAGE_COL:
                return self.data(index, Qt.DisplayRole)
        return QVariant()
            
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if section == self.TIME_COL:
                return QVariant("Time")
            elif section == self.SENDER_COL:
                return QVariant("Sender")
            elif section == self.MESSAGE_COL:
                return QVariant("Message")
        return super(MessagesTableModel, self).headerData(section, orientation, role)
            
    @loggingSlot(time.struct_time, object, object)
    def messagePrepended(self, _time, _sender, _message):
        self.rowsInserted.emit(QModelIndex(), 0, 0)

    @loggingSlot()
    def updateSenders(self):
        self.dataChanged.emit(self.createIndex(0, self.SENDER_COL),
                              self.createIndex(len(self._messages), self.SENDER_COL))
        
    def updateTimes(self):
        self.dataChanged.emit(self.createIndex(0, self.TIME_COL),
                              self.createIndex(len(self._messages), self.TIME_COL))
