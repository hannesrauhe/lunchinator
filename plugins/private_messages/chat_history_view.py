from PyQt4.QtGui import QWidget, QHBoxLayout, QTreeView
from lunchinator import get_db_connection, get_peers, log_warning
from lunchinator.table_models import TableModelBase
from Carbon.AppleEvents import pID

class HistoryPeersModel(TableModelBase):
    _NAME_KEY = u'name'
    _ID_KEY = u'ID'
    
    def __init__(self, dataSource):
        columns = [(u"Name", self._updateNameItem)]
        super(HistoryPeersModel, self).__init__(dataSource, columns)
            
    def _updateNameItem(self, pID, _data, item):
        m_name = get_peers().getDisplayedPeerName(pID=pID)
        if m_name == None:
            log_warning("displayed peer name (%s) should not be None" % pID)
            m_name = pID
        item.setText(m_name)
        
class ChatHistoryWidget(QWidget):
    def __init__(self, parent):
        super(ChatHistoryWidget, self).__init__(parent)
        
        self._peerModel = HistoryPeersModel(None)
        self._updatePeers()
        
        self._initPeerList()
        
        layout = QHBoxLayout(self)
        layout.addWidget(self._peerList)
      
    def _updatePeers(self):
        db, _type = get_db_connection()
        rows = db.query("select distinct PARTNER from PRIVATE_MESSAGES")

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
        self._peerList.setHeaderHidden(True)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(self._peerModel)
