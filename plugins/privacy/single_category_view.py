from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, QComboBox, QTreeView,\
    QVBoxLayout, QFrame, QCheckBox
from lunchinator.table_models import TableModelBase
from lunchinator import get_peers, log_warning, get_notification_center,\
    convert_string
from PyQt4.QtCore import Qt
from privacy.privacy_settings import PrivacySettings

class PeerModel(TableModelBase):
    def __init__(self, checked, unchecked):
        columns = [(u"Peer Name", self._updateNameItem)]
        super(PeerModel, self).__init__(None, columns)
        
        self._checked = checked if type(checked) is set else set(checked)
        self._unchecked = unchecked if type(unchecked) is set else set(unchecked)
        
        if get_peers() is not None:
            peers = get_peers().getAllKnownPeerIDs()
            for pID in peers:
                self.appendContentRow(pID, get_peers().getPeerInfo(pID=pID))
        
    def peerNameAdded(self, pID, _name):
        self.appendContentRow(pID, None)
    
    def peerNameChanged(self, pID, _newName):
        self.externalRowUpdated(pID, None)
        
    def _updateNameItem(self, pID, _data, item):
        m_name = get_peers().getDisplayedPeerName(pID=pID)
        if m_name == None:
            log_warning("displayed peer name (%s) should not be None" % pID)
            m_name = pID
        item.setText(m_name)
        item.setCheckable(True)
        item.setCheckState(Qt.Unchecked if pID in self._unchecked else Qt.Checked if pID in self._checked else Qt.PartiallyChecked)
        
class SingleCategoryView(QWidget):
    def __init__(self, action, parent, category=None, mode=None):
        super(SingleCategoryView, self).__init__(parent)
        
        self._action = action
        self._category = category
        
        if mode is not None:
            topWidget = None
        else:
            mode = PrivacySettings.get().getPolicy(self._action, self._category)
            topWidget = self._initTopView(mode)
            
        centralWidget = self._initPeerList()
        bottomWidget = self._initBottomWidget()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        if topWidget is not None:
            mainLayout.addWidget(topWidget)
        mainLayout.addWidget(centralWidget, 1)
        mainLayout.addWidget(bottomWidget)
        self._modeChanged(mode, False)
        
        get_notification_center().connectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().connectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        
    def finish(self):
        get_notification_center().disconnectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().disconnectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        
    def _initTopView(self, mode):
        topWidget = QWidget(self)
        
        self._modeCombo = QComboBox(topWidget)
        self._modeCombo.addItem(u"nobody")
        self._modeCombo.addItem(u"nobody, except")
        self._modeCombo.addItem(u"everybody, except")
        self._modeCombo.addItem(u"everybody")
        self._modeCombo.setCurrentIndex(mode)
        self._modeCombo.currentIndexChanged.connect(self._modeChanged)
        
        topLayout = QHBoxLayout(topWidget)
        topLayout.addWidget(QLabel(u"Accept from"), 0)
        topLayout.addWidget(self._modeCombo, 1, Qt.AlignLeft)
        return topWidget
        
    def _initPeerList(self):
        capsuleWidget = QWidget()
        capsuleLayout = QVBoxLayout(capsuleWidget)
        
        self._peerModel = PeerModel(PrivacySettings.get().getChecked(self._action, self._category),
                              PrivacySettings.get().getUnchecked(self._action, self._category))
        
        self._peerModel.itemChanged.connect(self._peerDataChanged)
        
        self._peerList = QTreeView(self)
        self._peerList.setAlternatingRowColors(False)
        self._peerList.setHeaderHidden(True)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(self._peerModel)
        self._peerList.setSelectionMode(QTreeView.SingleSelection)
        self._peerList.setAutoFillBackground(False)
        self._peerList.viewport().setAutoFillBackground(False)
        self._peerList.setFrameShape(QFrame.NoFrame)
        self._peerList.setFocusPolicy(Qt.NoFocus)
        
        capsuleLayout.addWidget(self._peerList)
        return capsuleWidget
    
    def _initBottomWidget(self):
        self._askForConfirmationBox = QCheckBox(u"Ask if state is unknown", self)
        self._askForConfirmationBox.setCheckState(Qt.Checked if PrivacySettings.get().getAskForConfirmation(self._action, self._category) else Qt.Unchecked)
        self._askForConfirmationBox.stateChanged.connect(self._askForConfirmationChanged)
        return self._askForConfirmationBox
    
    def _peerDataChanged(self, item):
        PrivacySettings.get().addException(self._action,
                                           self._category,
                                           convert_string(item.data(PeerModel.KEY_ROLE).toString()),
                                           item.checkState() == Qt.Checked)
    
    def _askForConfirmationChanged(self, newState):
        PrivacySettings.get().setAskForConfirmation(self._action, self._category, newState == Qt.Checked)
        
    def _modeChanged(self, newMode, notify=True):
        self._peerList.setVisible(newMode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX))
        self._askForConfirmationBox.setVisible(newMode == PrivacySettings.POLICY_NOBODY_EX)
        self._mode = newMode
        if notify:
            PrivacySettings.get().setPolicy(self._action, self._category, self._mode)
        
    def setMode(self, newMode):
        self._modeChanged(newMode)
