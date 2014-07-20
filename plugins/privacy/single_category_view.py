from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, QComboBox, QTreeView,\
    QVBoxLayout, QFrame
from lunchinator.table_models import TableModelBase
from lunchinator import get_peers, log_warning, get_notification_center
from PyQt4.QtCore import Qt
from privacy.settings_model import SettingsModel

class PeerModel(TableModelBase):
    def __init__(self):
        columns = [(u"Peer Name", self._updateNameItem)]
        super(PeerModel, self).__init__(None, columns)
        
        if get_peers() is not None:
            peers = get_peers().getPeers()
            for pID in peers:
                self.appendContentRow(pID, get_peers().getPeerInfo(pID=pID))
                
        get_notification_center().connectPeerAppended(self.externalRowAppended)
        get_notification_center().connectPeerUpdated(self.externalRowUpdated)
        get_notification_center().connectPeerRemoved(self.externalRowRemoved)
        
    def _updateNameItem(self, pID, _data, item):
        m_name = get_peers().getDisplayedPeerName(pID=pID)
        if m_name == None:
            log_warning("displayed peer name (%s) should not be None" % pID)
            m_name = pID
        item.setText(m_name)
        item.setCheckable(True)
        item.setCheckState(Qt.Unchecked)
        
class SingleCategoryView(QWidget):
    _peerModel = None
    
    @classmethod
    def getPeerModel(cls):
        if cls._peerModel is None:
            cls._peerModel = PeerModel()
        return cls._peerModel
            
    def __init__(self, action, parent, category=None, mode=None):
        super(SingleCategoryView, self).__init__(parent)
        
        if mode is not None:
            topWidget = None
        else:
            mode = 0
            topWidget = self._initTopView()
            
        centralWidget = self._initPeerList()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        if topWidget is not None:
            mainLayout.addWidget(topWidget)
        mainLayout.addWidget(centralWidget, 1)
        self.setMode(mode)
        
    def _initTopView(self):
        topWidget = QWidget(self)
        
        self._modeCombo = QComboBox(topWidget)
        self._modeCombo.addItem(u"nobody")
        self._modeCombo.addItem(u"nobody, except")
        self._modeCombo.addItem(u"everybody, except")
        self._modeCombo.addItem(u"everybody")
        self._modeCombo.currentIndexChanged.connect(self._modeChanged)
        
        topLayout = QHBoxLayout(topWidget)
        topLayout.addWidget(QLabel(u"Accept from"), 0)
        topLayout.addWidget(self._modeCombo, 1, Qt.AlignLeft)
        return topWidget
        
    def _initPeerList(self):
        capsuleWidget = QWidget()
        capsuleLayout = QVBoxLayout(capsuleWidget)
        
        self._peerList = QTreeView(self)
        self._peerList.setAlternatingRowColors(False)
        self._peerList.setHeaderHidden(True)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(self.getPeerModel())
        self._peerList.setSelectionMode(QTreeView.SingleSelection)
        self._peerList.setAutoFillBackground(False)
        self._peerList.viewport().setAutoFillBackground(False)
        self._peerList.setFrameShape(QFrame.NoFrame)
        self._peerList.setFocusPolicy(Qt.NoFocus)
        
        capsuleLayout.addWidget(self._peerList)
        return capsuleWidget
        
    def _modeChanged(self, newMode):
        self._peerList.setVisible(newMode in (SettingsModel.MODE_EVERYBODY_EX, SettingsModel.MODE_NOBODY_EX))
        self._mode = newMode
        
    def setMode(self, newMode):
        self._modeChanged(newMode)
