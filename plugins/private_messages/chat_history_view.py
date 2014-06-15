from PyQt4.QtGui import QWidget, QHBoxLayout, QTreeView,\
    QSplitter, QTextDocument
from lunchinator import get_db_connection, get_peers, log_warning,\
    convert_string
from lunchinator.table_models import TableModelBase
from Carbon.AppleEvents import pID
from lunchinator.utilities import formatTime
from time import localtime
from PyQt4.QtCore import Qt

class HistoryPeersModel(TableModelBase):
    _NAME_KEY = u'name'
    _ID_KEY = u'ID'
    
    def __init__(self, dataSource):
        columns = [(u"Chat Partner", self._updateNameItem)]
        super(HistoryPeersModel, self).__init__(dataSource, columns)
            
    def _updateNameItem(self, pID, _data, item):
        m_name = get_peers().getDisplayedPeerName(pID=pID)
        if m_name == None:
            log_warning("displayed peer name (%s) should not be None" % pID)
            m_name = pID
        item.setText(m_name)
        
class ChatHistoryModel(TableModelBase):
    def __init__(self, dataSource, partnerName, rows):
        columns = [(u"Sender", self._updateSenderItem),
                   (u"Time", self._updateTimeItem),
                   (u"Message", self._updateMessageItem)]
        self._partnerName = partnerName
        super(ChatHistoryModel, self).__init__(dataSource, columns)
        
        self._doc = QTextDocument(self)
        
        # M_ID, IS_OWN_MESSAGE, TIME, MESSAGE
        for row in rows:
            self.appendContentRow(row[0], row)
            
    def _updateSenderItem(self, _msgID, row, item):
        if row[1]: # is own message
            item.setText(u"You")
        else:
            item.setText(self._partnerName)
            
    def _updateTimeItem(self, _msgID, row, item):
        mTime = localtime(row[2])
        item.setText(formatTime(mTime))
            
    def _updateMessageItem(self, _msgID, row, item):
        self._doc.setHtml(row[3])
        item.setText(self._doc.toPlainText())
        
class ChatHistoryWidget(QWidget):
    def __init__(self, parent):
        super(ChatHistoryWidget, self).__init__(parent)
        
        self._db, _type = get_db_connection()
        
        self._peerModel = HistoryPeersModel(None)
        self._updatePeers()
        
        self._initPeerList()
        self._initHistoryTable()
        
        split = QSplitter(Qt.Horizontal, self)
        split.addWidget(self._peerList)
        split.addWidget(self._historyTable)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
      
        layout = QHBoxLayout(self)
        layout.addWidget(split)
        
    def _updatePeers(self):
        rows = self._db.query("select distinct PARTNER from PRIVATE_MESSAGES")

        newPeers = {}      
        with get_peers():
            for row in rows:
                pID = row[0]
                newPeers[pID] = get_peers().getPeerInfo(pID=pID, lock=False)
        for pID, peerInfo in newPeers.iteritems():
            if self._peerModel.hasKey(pID):
                self._peerModel.externalRowUpdated(pID, peerInfo)
            else:
                self._peerModel.externalRowAppended(pID, peerInfo)
      
    def _initPeerList(self):  
        self._peerList = QTreeView(self)
        self._peerList.setAlternatingRowColors(True)
        self._peerList.setHeaderHidden(False)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(self._peerModel)
        self._peerList.setSelectionMode(QTreeView.SingleSelection)
        self._peerList.selectionModel().selectionChanged.connect(self._displayHistory)

    def _displayHistory(self, newSelection, _oldSelection):
        if len(newSelection.indexes()) > 0:
            index = iter(newSelection.indexes()).next()
            partnerID = convert_string(index.data(HistoryPeersModel.KEY_ROLE).toString())
            self._createHistoryModel(partnerID)

    def _initHistoryTable(self):
        self._historyTable = QTreeView(self)
        self._historyTable.setAlternatingRowColors(True)
        self._historyTable.setHeaderHidden(False)
        self._historyTable.setItemsExpandable(False)
        self._historyTable.setIndentation(0)

    def _createHistoryModel(self, partnerID):
        rows = self._db.query("select M_ID, IS_OWN_MESSAGE, TIME, MESSAGE from PRIVATE_MESSAGES where PARTNER = ?", partnerID)
        historyModel = ChatHistoryModel(None, get_peers().getDisplayedPeerName(pID=partnerID), rows)
        self._historyTable.setModel(historyModel)
            
        