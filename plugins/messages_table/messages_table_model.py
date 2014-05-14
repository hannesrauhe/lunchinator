from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QVariant, QSize
from lunchinator import get_server, get_peers
import time
from time import mktime
from datetime import datetime, timedelta

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
            if index.column() == 0:
                mTime = self._getMessage(index.row())[0]
                return QVariant(time.mktime(mTime))
            else:
                # return display role as fallback
                return self.data(index)
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
