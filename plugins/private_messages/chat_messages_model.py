from PyQt4.QtGui import QStandardItemModel, QStandardItem
from PyQt4.QtCore import Qt, QVariant, QSize
from lunchinator.utilities import formatTime
from time import localtime

class ChatMessagesModel(QStandardItemModel):
    MESSAGE_STATE_OK = 0
    MESSAGE_STATE_NOT_DELIVERED = 1
    MESSAGE_STATE_ERROR = 2
    
    STATUS_ICON_ROLE = Qt.UserRole + 1
    OWN_MESSAGE_ROLE = STATUS_ICON_ROLE + 1
    MESSAGE_STATE_ROLE = OWN_MESSAGE_ROLE + 1
    MESSAGE_TIME_ROLE = MESSAGE_STATE_ROLE + 1
    
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
            
        toolTip += u"Sent " + formatTime(localtime(messageTime))
        if recvTime != None:
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
        
        if messageState == self.MESSAGE_STATE_NOT_DELIVERED:
            item.setData(QVariant(self._delegate.getWarnIcon()), ChatMessagesModel.STATUS_ICON_ROLE)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(self._delegate.getErrorIcon()), ChatMessagesModel.STATUS_ICON_ROLE)
        
        toolTip = self._createToolTipText(ownMessage, toolTip, messageTime, recvTime)
        
        if toolTip:
            item.setData(QVariant(toolTip), Qt.ToolTipRole)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(u"Unknown error, message could not be delivered."), Qt.ToolTipRole)
        elif messageState == self.MESSAGE_STATE_NOT_DELIVERED:
            item.setData(QVariant(u"Message not delivered."), Qt.ToolTipRole)
        item.setData(ownMessage, ChatMessagesModel.OWN_MESSAGE_ROLE)
        return item
    
    def _createEmptyItem(self):
        item = QStandardItem()
        item.setEditable(False)
        return item
    
    def messageDelivered(self, msgID, recvTime, error, errorMessage):
        """Used for delayed deliveries"""
        if msgID in self._idToRow:
            row = self._idToRow[msgID]
            item = self.item(row, self.MESSAGE_COLUMN)
            state, _ = item.data(self.MESSAGE_STATE_ROLE).toInt()
            messageTime, _ = item.data(self.MESSAGE_TIME_ROLE).toDouble()
            if state == self.MESSAGE_STATE_NOT_DELIVERED:
                item.setData(QVariant(self.MESSAGE_STATE_ERROR if error else self.MESSAGE_STATE_OK), self.MESSAGE_STATE_ROLE)
                toolTip = self._createToolTipText(True, errorMessage, messageTime, recvTime)
                item.setData(QVariant(toolTip), Qt.ToolTipRole)
                item.setData(QVariant(QVariant(self._delegate.getErrorIcon()) if error else QVariant()), self.STATUS_ICON_ROLE)
                return True
        return False
        
    def getLastIndex(self):
        return self.index(self.rowCount() - 1, 1)