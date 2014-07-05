from PyQt4.QtGui import QWidget, QHBoxLayout, QTreeView,\
    QSplitter, QTextDocument, QStandardItemModel, QSortFilterProxyModel,\
    QLineEdit, QVBoxLayout
from lunchinator import get_db_connection, get_peers, log_warning,\
    convert_string
from lunchinator.table_models import TableModelBase
from lunchinator.utilities import formatTime
from time import localtime
from PyQt4.QtCore import Qt, QVariant

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
        
class ChatHistoryModel(QStandardItemModel):
    def __init__(self, partnerID, rows):
        super(ChatHistoryModel, self).__init__()

        self.setHorizontalHeaderLabels([u"Sender", u"Send Time", u"Text"])
        
        self.insertRows(0, len(rows));
    
        partnerName = get_peers().getDisplayedPeerName(pID=partnerID)
        doc = QTextDocument()
        for i, row in enumerate(rows):
            # sender
            index = self.index(i, 0);
            if row[1]: # is own message
                self.setData(index, QVariant(u"You"))
            else:
                self.setData(index, partnerName)
                
            # time
            index = self.index(i, 1)
            mTime = localtime(row[2])
            self.setData(index, QVariant(formatTime(mTime)))
            
            # message
            index = self.index(i, 2)
            doc.setHtml(row[3])
            self.setData(index, QVariant(doc.toPlainText()));  
        
class ChatHistoryWidget(QWidget):
    def __init__(self, parent):
        super(ChatHistoryWidget, self).__init__(parent)
        
        self._db, _type = get_db_connection()
        
        self._peerModel = HistoryPeersModel(None)
        self._updatePeers()
        
        self._initPeerList()
        self._initHistoryTable()
        self._initSortFilterModel()
        
        topWidget = self._initTopWidget()
        mainWidget = self._initMainWidget()
      
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(topWidget, 0)
        layout.addWidget(mainWidget, 1)
        
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
        
    def _initMainWidget(self):
        split = QSplitter(Qt.Horizontal, self)
        split.addWidget(self._peerList)
        split.addWidget(self._historyTable)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        return split
    
    def _initTopWidget(self):
        topWidget = QWidget(self)
        self._searchField = QLineEdit(topWidget)
        if hasattr(self._searchField, "setPlaceholderText"):
            self._searchField.setPlaceholderText("Filter Messages")
        self._searchField.textChanged.connect(self._sortFilterModel.setFilterRegExp)
            
        layout = QHBoxLayout(topWidget)
        layout.setContentsMargins(0, 10, 10, 0)
        layout.addWidget(self._searchField, 0, Qt.AlignRight)
        return topWidget
      
    def _initSortFilterModel(self):
        self._sortFilterModel = QSortFilterProxyModel(self)
        self._sortFilterModel.setFilterKeyColumn(2)
        self._sortFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._historyTable.setModel(self._sortFilterModel)

    def _createHistoryModel(self, partnerID):
        rows = self._db.query("select M_ID, IS_OWN_MESSAGE, TIME, MESSAGE from PRIVATE_MESSAGES where PARTNER = ?", partnerID)
        historyModel = ChatHistoryModel(partnerID, rows)
        
        self._sortFilterModel.setSourceModel(historyModel)
