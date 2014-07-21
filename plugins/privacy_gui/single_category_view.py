from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, QComboBox, QTreeView,\
    QVBoxLayout, QFrame, QCheckBox
from lunchinator.table_models import TableModelBase
from lunchinator import get_peers, log_warning, get_notification_center,\
    convert_string
from PyQt4.QtCore import Qt
from lunchinator.privacy.privacy_settings import PrivacySettings

class PeerModel(TableModelBase):
    def __init__(self, data, tristate):
        columns = [(u"Peer Name", self._updateNameItem)]
        super(PeerModel, self).__init__(None, columns)
        
        if data is None:
            raise ValueError("data cannot be None")
        self._data = data
        self._tristate = tristate
        
        if get_peers() is not None:
            peers = get_peers().getAllKnownPeerIDs()
            for pID in peers:
                self.appendContentRow(pID, get_peers().getPeerInfo(pID=pID))
        
    def setExceptionData(self, data):
        if data is None:
            raise ValueError("data cannot be None")
        self._data = data
        self.updateColumn(0)
    
    def _dataForKey(self, _key):
        return None
        
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
        item.setTristate(self._tristate)
        if pID in self._data:
            checkState = Qt.Checked if self._data[pID] == 1 else Qt.Unchecked
        else:
            checkState = Qt.PartiallyChecked
        item.setCheckState(checkState)
        
class SingleCategoryView(QWidget):
    def __init__(self, action, parent, category=None, mode=None):
        super(SingleCategoryView, self).__init__(parent)
        
        self._action = action
        self._category = category
        
        if mode is not None:
            topWidget = None
            self._determineOwnMode = False
        else:
            self._determineOwnMode = True
            mode = PrivacySettings.get().getPolicy(self._action, self._category, useModified=True)
            topWidget = self._initTopView(mode)
            
        centralWidget = self._initPeerList(mode)
        bottomWidget = self._initBottomWidget()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        if topWidget is not None:
            mainLayout.addWidget(topWidget)
        mainLayout.addWidget(centralWidget, 1)
        mainLayout.addWidget(bottomWidget)
        self._modeChanged(mode, notify=False, resetModel=False)
        
        get_notification_center().connectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().connectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        get_notification_center().connectPrivacySettingsChanged(self._privacySettingsChanged)
        
    def finish(self):
        get_notification_center().disconnectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().disconnectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        get_notification_center().disconnectPrivacySettingsChanged(self._privacySettingsChanged)
        
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
        
    def _initPeerList(self, mode):
        capsuleWidget = QWidget()
        capsuleLayout = QVBoxLayout(capsuleWidget)
        
        self._peerModel = PeerModel(PrivacySettings.get().getExceptions(self._action, self._category, mode, useModified=True),
                                    mode == PrivacySettings.POLICY_PEER_EXCEPTION)
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
        self._askForConfirmationBox.stateChanged.connect(self._askForConfirmationChanged)
        return self._askForConfirmationBox
    
    def _peerDataChanged(self, item):
        PrivacySettings.get().addException(self._action,
                                           self._category,
                                           self._mode,
                                           convert_string(item.data(PeerModel.KEY_ROLE).toString()),
                                           1 if item.checkState() == Qt.Checked else 0 if item.checkState() == Qt.Unchecked else -1,
                                           applyImmediately=False)
    
    def _askForConfirmationChanged(self, newState):
        PrivacySettings.get().setAskForConfirmation(self._action, self._category, newState == Qt.Checked, applyImmediately=False)
        
    def _modeChanged(self, newMode, notify=True, resetModel=True):
        if newMode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
            if resetModel:
                # no change notifications, we are just resetting the model
                self._peerModel.itemChanged.disconnect(self._peerDataChanged)
                self._peerModel.setExceptionData(PrivacySettings.get().getExceptions(self._action, self._category, newMode, useModified=True))
                self._peerModel.itemChanged.connect(self._peerDataChanged)
            self._peerList.setVisible(True)
        else:
            self._peerList.setVisible(False)
        self._askForConfirmationBox.setCheckState(Qt.Checked if PrivacySettings.get().getAskForConfirmation(self._action, self._category, useModified=True) else Qt.Unchecked)
        self._askForConfirmationBox.setVisible(newMode == PrivacySettings.POLICY_NOBODY_EX)
        self._mode = newMode
        if notify:
            PrivacySettings.get().setPolicy(self._action, self._category, self._mode, applyImmediately=False)
        
    def setMode(self, newMode):
        self._modeChanged(newMode)

    def _privacySettingsChanged(self, pluginName, actionName):
        if pluginName != self._action.getPluginName() or actionName != self._action.getName():
            return
        if self._determineOwnMode:
            newMode = PrivacySettings.get().getPolicy(self._action, self._category)
        else:
            newMode = self._mode
        self._modeChanged(newMode, notify=False)