from private_messages.chat_messages_storage import ChatMessagesStorage
from private_messages.message_item_delegate import MessageItemDelegate
from private_messages.chat_messages_model import ChatMessagesModel
from lunchinator import get_peers,  convert_string
from lunchinator.table_models import TableModelBase
from lunchinator.utilities import formatTime, getPlatform, PLATFORM_MAC
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.log.logging_func import loggingFunc

from PyQt4.QtGui import QWidget, QHBoxLayout, QTreeView,\
    QSplitter, QStandardItemModel, QSortFilterProxyModel,\
    QLineEdit, QVBoxLayout, QPushButton, QFrame, QToolButton, QMenu,\
    QStandardItem, QItemSelection
from PyQt4.QtCore import Qt, QVariant

from time import localtime
from functools import partial

class HistoryPeersModel(TableModelBase):
    _NAME_KEY = u'name'
    _ID_KEY = u'ID'
    
    def __init__(self, dataSource, logger):
        columns = [(u"Chat Partner", self._updateNameItem)]
        super(HistoryPeersModel, self).__init__(dataSource, columns, logger)
            
    def _updateNameItem(self, pID, _data, item):
        m_name = get_peers().getDisplayedPeerName(pID=pID)
        if m_name == None:
            self.logger.warning("displayed peer name (%s) should not be None", pID)
            m_name = pID
        item.setText(m_name)
        
class ChatHistoryModel(QStandardItemModel):
    def __init__(self, partnerID, rows):
        super(ChatHistoryModel, self).__init__()

        self.setHorizontalHeaderLabels([u"Sender", u"Send Time", u"Text"])
        
        if get_peers() is not None:
            partnerName = get_peers().getDisplayedPeerName(pID=partnerID)
        else:
            partnerName = partnerID
        for row in rows:
            # sender
            item1 = self._createItem()
            isOwn = row[ChatMessagesStorage.MSG_IS_OWN_MESSAGE_COL] != 0
            if isOwn:
                item1.setData(QVariant(u"You"), Qt.DisplayRole)
            else:
                item1.setData(partnerName, Qt.DisplayRole)
                
            # time
            item2 = self._createItem()
            mTime = localtime(row[ChatMessagesStorage.MSG_TIME_COL])
            item2.setData(QVariant(formatTime(mTime)), Qt.DisplayRole)
            
            # message
            item3 = self._createItem(True)
            item3.setData(QVariant(row[ChatMessagesStorage.MSG_TEXT_COL]), Qt.DisplayRole)
            item3.setData(QVariant(isOwn), ChatMessagesModel.OWN_MESSAGE_ROLE)
            
            self.appendRow([item1, item2, item3])
    
    def _createItem(self, editable=False):
        item = QStandardItem()
        item.setEditable(editable)
        return item
        
class HistoryTable(QTreeView):
    def __init__(self, parent, logger):
        super(HistoryTable, self).__init__(parent)
        
        self.logger = logger
        self.setAlternatingRowColors(False)
        self.setHeaderHidden(False)
        self.setItemsExpandable(False)
        self.setIndentation(0)
        self.setItemDelegate(MessageItemDelegate(self, logger, column=2, margin=0))
        self.setSelectionMode(QTreeView.NoSelection)
                
        self.setObjectName(u"__peer_list")
        self.setFrameShape(QFrame.StyledPanel)
        if getPlatform() == PLATFORM_MAC:
            self.setStyleSheet("QFrame#__peer_list{border-width: 1px; border-top-style: solid; border-right-style: none; border-bottom-style: none; border-left-style: solid; border-color:palette(mid)}");
        
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.column() == 2 and self.itemDelegate().shouldStartEditAt(event.pos(), index):
                # do not start editing if already editing
                if index != self.itemDelegate().getEditIndex():
                    self.stopEditing()
                    self.itemDelegate().setEditIndex(index)
                    self.edit(index)
            else:
                # clicked somewhere else -> stop editing
                self.stopEditing()
        super(HistoryTable, self).mousePressEvent(event)

    def stopEditing(self):
        if self.itemDelegate().getEditor() != None:
            self.closeEditor(self.itemDelegate().getEditor(), MessageItemDelegate.NoHint)
            self.itemDelegate().editorClosing(self.itemDelegate().getEditor(), MessageItemDelegate.NoHint)
        
        
class ChatHistoryWidget(QWidget):
    def __init__(self, delegate, parent, logger):
        super(ChatHistoryWidget, self).__init__(parent)
        
        self.logger = logger
        self._delegate = delegate
        
        self._peerModel = HistoryPeersModel(None, self.logger)
        self._updatePeers()
        
        self._initPeerList()
        self._initHistoryTable()
        self._initSortFilterModel()
        
        topWidget = self._initTopWidget()
        mainWidget = self._initMainWidget()
      
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(topWidget, 0)
        layout.addWidget(mainWidget, 1)
      
    def _initPeerList(self):  
        self._peerList = QTreeView(self)
        self._peerList.setAlternatingRowColors(True)
        self._peerList.setHeaderHidden(False)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(self._peerModel)
        self._peerList.setSelectionMode(QTreeView.SingleSelection)
        self._peerList.selectionModel().selectionChanged.connect(self._displayHistory)
        
        self._peerList.setObjectName(u"__peer_list")
        self._peerList.setFrameShape(QFrame.StyledPanel)
        if getPlatform() == PLATFORM_MAC:
            self._peerList.setStyleSheet("QFrame#__peer_list{border-width: 1px; border-top-style: solid; border-right-style: solid; border-bottom-style: none; border-left-style: none; border-color:palette(mid)}");

    def _initHistoryTable(self):
        self._historyTable = HistoryTable(self, self.logger)
        
    def _initMainWidget(self):
        split = QSplitter(Qt.Horizontal, self)
        split.addWidget(self._peerList)
        split.addWidget(self._historyTable)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        return split
    
    def _initTopWidget(self):
        topWidget = QWidget(self)
        
        refreshButton = QPushButton("Refresh", topWidget)
        refreshButton.clicked.connect(self._updatePeers)
        
        self._clearButton = QPushButton("Clear Selected", topWidget)
        self._clearButton.setEnabled(False)
        self._clearButton.clicked.connect(self._clearSelected)
        
        self._openChatButton = QToolButton(topWidget)
        self._openChatButton.setText(u"Open chat with ")
        self._openChatButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._openChatButton.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self._openChatButton)
        menu.aboutToShow.connect(partial(self._fillPeersPopup, menu))
        self._openChatButton.setMenu(menu)
        
        self._searchField = QLineEdit(topWidget)
        if hasattr(self._searchField, "setPlaceholderText"):
            self._searchField.setPlaceholderText("Filter Messages")
        self._searchField.textChanged.connect(self._sortFilterModel.setFilterRegExp)
            
        layout = QHBoxLayout(topWidget)
        layout.setContentsMargins(0, 10, 10, 0)
        layout.addWidget(refreshButton, 0, Qt.AlignLeft)
        layout.addWidget(self._clearButton, 0, Qt.AlignLeft)
        layout.addWidget(self._openChatButton, 1, Qt.AlignLeft)
        layout.addWidget(self._searchField, 0, Qt.AlignRight)
        return topWidget
      
    def _initSortFilterModel(self):
        self._sortFilterModel = QSortFilterProxyModel(self)
        self._sortFilterModel.setFilterKeyColumn(2)
        self._sortFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._historyTable.setModel(self._sortFilterModel)

    def _createHistoryModel(self, partnerID):
        rows = self._delegate.getStorage().getMessages(partnerID) 
        historyModel = ChatHistoryModel(partnerID, rows)
        self._sortFilterModel.setSourceModel(historyModel)

    @loggingFunc
    def _fillPeersPopup(self, menu):
        menu.clear()
        
        if get_peers() is None:
            self.logger.warning("no lunch_peers instance available, cannot show peer actions")
            return
        
        with get_peers():
            for peerID in get_peers():
                peerInfo = get_peers().getPeerInfo(pID=peerID, lock=False)
                if self._delegate.getOpenChatAction().appliesToPeer(peerID, peerInfo):
                    menu.addAction(get_peers().getDisplayedPeerName(pID=peerID, lock=False), partial(self._openChat, peerID))
        
    def _openChat(self, peerID):
        peerInfo = get_peers().getPeerInfo(pID=peerID)
        if peerInfo is None:
            self.logger.error("No peer info found for peer %s", peerID)
            return
        
        self._delegate.getOpenChatAction().performAction(peerID, peerInfo, self)

    @loggingSlot()
    def _updatePeers(self):
        if get_peers() is None:
            return
        rows = self._delegate.getStorage().getPartners()

        newPeers = {}   
        with get_peers():
            for row in rows:
                pID = row[0]
                newPeers[pID] = get_peers().getPeerInfo(pID=pID, lock=False)
        self._peerModel.removeMissingKeys(newPeers.keys())
        for pID, peerInfo in newPeers.iteritems():
            if self._peerModel.hasKey(pID):
                self._peerModel.externalRowUpdated(pID, peerInfo)
            else:
                self._peerModel.externalRowAppended(pID, peerInfo)
                
    @loggingSlot(QItemSelection, QItemSelection)
    def _displayHistory(self, newSelection, _oldSelection):
        if len(newSelection.indexes()) > 0:
            index = iter(newSelection.indexes()).next()
            partnerID = convert_string(index.data(HistoryPeersModel.KEY_ROLE).toString())
            self._createHistoryModel(partnerID)
            self._clearButton.setEnabled(True)
        else:
            self._sortFilterModel.setSourceModel(None)
            self._clearButton.setEnabled(False)
            
    @loggingSlot()
    def _clearSelected(self):
        if not self._peerList.selectionModel().hasSelection():
            return
        selection = self._peerList.selectionModel().selection()
        if len(selection.indexes()) > 0:
            index = iter(selection.indexes()).next()
            partnerID = convert_string(index.data(HistoryPeersModel.KEY_ROLE).toString())
            self._delegate.getStorage().clearHistory(partnerID)
            self._peerModel.externalRowRemoved(partnerID)
