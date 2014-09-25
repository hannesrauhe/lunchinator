from PyQt4.QtGui import QStandardItemModel, QStandardItem
from PyQt4.QtCore import Qt, QVariant, QSize
from lunchinator.utilities import formatTime
from time import localtime
from lunchinator import convert_string

class ChatMessagesModel(QStandardItemModel):
    MESSAGE_STATE_OK = 0
    MESSAGE_STATE_NOT_DELIVERED = 1
    MESSAGE_STATE_ERROR = 2
    
    STATUS_ICON_ROLE = Qt.UserRole + 1
    OWN_MESSAGE_ROLE = STATUS_ICON_ROLE + 1
    MESSAGE_STATE_ROLE = OWN_MESSAGE_ROLE + 1
    MESSAGE_TIME_ROLE = MESSAGE_STATE_ROLE + 1
    RECV_TIME_ROLE = MESSAGE_TIME_ROLE + 1
    TOOL_TIP_MSG_ROLE = RECV_TIME_ROLE + 1
    
    OTHER_ICON_COLUMN = 0
    MESSAGE_COLUMN = 1
    OWN_ICON_COLUMN = 2
    
    def __init__(self, delegate, parent):
        super(ChatMessagesModel, self).__init__(parent)
        self._delegate = delegate
        self.setColumnCount(3)
        self._idToRow = {}

    def addOwnMessage(self, msgID, recvTime, msg, msgTime, messageState=None, toolTip=None):
        self._idToRow[msgID] = self.rowCount()
        self.appendRow([self._createEmptyItem(),
                        self._createMessageItem(msg, msgTime, True, messageState, toolTip, recvTime),
                        self._createIconItem(self._delegate.getOwnIcon())])
        
    def addOtherMessage(self, msg, msgTime, recvTime):
        self.appendRow([self._createIconItem(self._delegate.getOtherIcon()),
                        self._createMessageItem(msg, msgTime, False, recvTime=recvTime),
                        self._createEmptyItem()])
        
    def addTimeRow(self, rtime):
        self.appendRow([self._createTimeItem(rtime), self._createTimeItem(rtime), self._createTimeItem(rtime)])
        
    def setOwnIcon(self, icon):
        for row in xrange(self.rowCount()):
            self.item(row, self.OWN_ICON_COLUMN).setData(QVariant(icon), Qt.DecorationRole)
            
    def setOtherIcon(self, icon):
        for row in xrange(self.rowCount()):
            self.item(row, self.OTHER_ICON_COLUMN).setData(QVariant(icon), Qt.DecorationRole)
        
    def _createTimeItem(self, rtime):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(rtime), Qt.DisplayRole)
        return item
        
    def _createIconItem(self, icon):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(icon), Qt.DecorationRole)
        item.setData(QSize(32, 32), Qt.SizeHintRole)
        return item
        
    def _createToolTipText(self, isOwn, toolTip, messageTime, recvTime):
        if toolTip:
            toolTip += u"\n"
        else:
            toolTip = u""
            
        toolTip += u"Sent: " + formatTime(localtime(messageTime))
        if recvTime:
            if isOwn:
                toolTip += ",\nDelivered: " + formatTime(localtime(recvTime))
            else:
                toolTip += ",\nReceived: " + formatTime(localtime(recvTime))
        return toolTip
        
    def _createMessageItem(self, msg, messageTime, ownMessage, messageState=None, toolTip=None, recvTime=None):
        item = QStandardItem()
        item.setEditable(True)
        item.setData(msg, Qt.DisplayRole)
        
        if messageState == None:
            messageState = self.MESSAGE_STATE_OK
            
        item.setData(QVariant(messageState), self.MESSAGE_STATE_ROLE)
        item.setData(QVariant(messageTime), self.MESSAGE_TIME_ROLE)
        if recvTime:
            item.setData(QVariant(recvTime), self.RECV_TIME_ROLE)
        
        if messageState == self.MESSAGE_STATE_NOT_DELIVERED:
            item.setData(QVariant(self._delegate.getWarnIcon()), ChatMessagesModel.STATUS_ICON_ROLE)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(self._delegate.getErrorIcon()), ChatMessagesModel.STATUS_ICON_ROLE)
        
        if toolTip:
            item.setData(QVariant(toolTip), self.TOOL_TIP_MSG_ROLE)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(u"Unknown error, message could not be delivered."), self.TOOL_TIP_MSG_ROLE)
        elif messageState == self.MESSAGE_STATE_NOT_DELIVERED:
            item.setData(QVariant(u"Message not delivered."), self.TOOL_TIP_MSG_ROLE)
        item.setData(ownMessage, ChatMessagesModel.OWN_MESSAGE_ROLE)
        return item
    
    def _createEmptyItem(self):
        item = QStandardItem()
        item.setEditable(False)
        return item
    
    def data(self, index, role=Qt.DisplayRole):
        if index.column() is 1 and role == Qt.ToolTipRole:
            isOwn = index.data(self.OWN_MESSAGE_ROLE).toBool()
            toolTip = convert_string(index.data(self.TOOL_TIP_MSG_ROLE).toString())
            messageTime, _ = index.data(self.MESSAGE_TIME_ROLE).toDouble()
            recvTime, _ = index.data(self.RECV_TIME_ROLE).toDouble()
            return self._createToolTipText(isOwn, toolTip, messageTime, recvTime)
        return QStandardItemModel.data(self, index, role)
    
    def messageDelivered(self, msgID, recvTime, error, errorMessage):
        """Used for delayed deliveries"""
        if msgID in self._idToRow:
            row = self._idToRow[msgID]
            item = self.item(row, self.MESSAGE_COLUMN)
            state, _ = item.data(self.MESSAGE_STATE_ROLE).toInt()
            if state == self.MESSAGE_STATE_NOT_DELIVERED:
                item.setData(QVariant(recvTime), self.RECV_TIME_ROLE)
                item.setData(QVariant(self.MESSAGE_STATE_ERROR if error else self.MESSAGE_STATE_OK), self.MESSAGE_STATE_ROLE)
                item.setData(QVariant(errorMessage) if errorMessage else QVariant(), self.TOOL_TIP_MSG_ROLE)
                item.setData(QVariant(QVariant(self._delegate.getErrorIcon()) if error else QVariant()), self.STATUS_ICON_ROLE)
                return True
        return False
        
    def messageIDChanged(self, oldID, newID):
        if oldID in self._idToRow:
            self._idToRow[newID] = self._idToRow[oldID]
            del self._idToRow[oldID]
        
        
    def getLastIndex(self):
        return self.index(self.rowCount() - 1, 1)