from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, QComboBox, QTreeView,\
    QVBoxLayout, QFrame, QCheckBox, QSortFilterProxyModel, QStandardItem
from PyQt4.QtCore import Qt, QVariant
from lunchinator.table_models import TableModelBase
from lunchinator import get_peers, get_notification_center,\
    convert_string
from lunchinator.log import getLogger
from lunchinator.privacy.privacy_settings import PrivacySettings
from lunchinator.log.logging_slot import loggingSlot

class PeerModel(TableModelBase):
    def __init__(self, data, tristate):
        columns = [(u"Peer Name", self._updateNameItem)]
        super(PeerModel, self).__init__(get_peers(), columns)
        
        if data is None:
            raise ValueError("data cannot be None")
        self._data = data
        self._tristate = tristate
        
        if self.dataSource is not None:
            peers = self.dataSource.getAllKnownPeerIDs()
            for pID in peers:
                self.appendContentRow(pID, None)
        else:
            for i in range(20):
                self.appendContentRow("test %d" % i, None)
        
    def setExceptionData(self, data):
        if data is None:
            raise ValueError("data cannot be None")
        self._data = data
        self.updateColumn(0)
    
    def _dataForKey(self, _key):
        return None
    
    def setData(self, index, value, role):
        if self._tristate and role == Qt.CheckStateRole:
            newState, _ = value.toInt()
            if newState == Qt.Checked:
                curState, _ = index.data(Qt.CheckStateRole).toInt()
                if curState == Qt.Unchecked:
                    value = QVariant(Qt.PartiallyChecked)
        return TableModelBase.setData(self, index, value, role)
        
    @loggingSlot(object, object)
    def peerNameAdded(self, pID, _name):
        self.appendContentRow(pID, None)
    
    @loggingSlot(object, object)
    def peerNameChanged(self, pID, _newName):
        self.externalRowUpdated(pID, None)
        
    def _updateNameItem(self, pID, _data, item):
        if self.dataSource is not None:
            m_name = self.dataSource.getDisplayedPeerName(pID=pID)
        else:
            m_name = pID
        
        if m_name is None:
            getLogger().warning("displayed peer name (%s) should not be None", pID)
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
        self._resetting = False
        
        if mode is not None:
            topWidget = None
            self._determineOwnMode = False
        else:
            self._determineOwnMode = True
            mode = PrivacySettings.get().getPolicy(self._action, self._category, useModified=True, categoryPolicy=self._getCategoryPolicy())
            topWidget = self._initTopView(mode)
            
        centralWidget = self._initPeerList(mode)
        bottomWidget = self._initBottomWidget()
        
        mainLayout = QVBoxLayout(self)
        if topWidget is None:
            # inside multiple categories view -> no margins
            mainLayout.setContentsMargins(0, 0, 0, 0)
        if topWidget is not None:
            mainLayout.addWidget(topWidget)
        mainLayout.addWidget(centralWidget, 1)
        mainLayout.addWidget(bottomWidget)
        self._modeChanged(mode, notify=False, resetModel=False)
        
        get_notification_center().connectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().connectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        get_notification_center().connectPrivacySettingsChanged(self._privacySettingsChanged)
        get_notification_center().connectPrivacySettingsDiscarded(self._privacySettingsChanged)
        
    def finish(self):
        get_notification_center().disconnectPeerNameAdded(self._peerModel.peerNameAdded)
        get_notification_center().disconnectDisplayedPeerNameChanged(self._peerModel.peerNameChanged)
        get_notification_center().disconnectPrivacySettingsChanged(self._privacySettingsChanged)
        get_notification_center().disconnectPrivacySettingsDiscarded(self._privacySettingsChanged)
        
    def _getCategoryPolicy(self):
        return PrivacySettings.CATEGORY_NEVER if self._category is None else PrivacySettings.CATEGORY_ALWAYS
        
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
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.addWidget(QLabel(u"Accept from"), 0)
        topLayout.addWidget(self._modeCombo, 1, Qt.AlignLeft)
        return topWidget
        
    def _initPeerList(self, mode):
        capsuleWidget = QWidget()
        capsuleLayout = QVBoxLayout(capsuleWidget)
        capsuleLayout.setContentsMargins(10, 0, 10, 0)
        
        if mode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX, PrivacySettings.POLICY_PEER_EXCEPTION):
            exceptions = PrivacySettings.get().getExceptions(self._action, self._category, mode, useModified=True, categoryPolicy=self._getCategoryPolicy())
        else:
            exceptions = {}
        self._peerModel = PeerModel(exceptions,
                                    mode == PrivacySettings.POLICY_PEER_EXCEPTION)
        self._peerModel.itemChanged.connect(self._peerDataChanged)
        
        proxyModel = QSortFilterProxyModel(self)
        proxyModel.setDynamicSortFilter(True)
        proxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxyModel.setSourceModel(self._peerModel)
        proxyModel.sort(0)
        
        self._peerList = QTreeView(self)
        self._peerList.setAlternatingRowColors(False)
        self._peerList.setHeaderHidden(True)
        self._peerList.setItemsExpandable(False)
        self._peerList.setIndentation(0)
        self._peerList.setModel(proxyModel)
        self._peerList.setSelectionMode(QTreeView.NoSelection)
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
    
    @loggingSlot(QStandardItem)
    def _peerDataChanged(self, item):
        if not self._resetting:
            PrivacySettings.get().addException(self._action,
                                               self._category,
                                               self._mode,
                                               convert_string(item.data(PeerModel.KEY_ROLE).toString()),
                                               1 if item.checkState() == Qt.Checked else 0 if item.checkState() == Qt.Unchecked else -1,
                                               applyImmediately=False,
                                               categoryPolicy=self._getCategoryPolicy())
    
    @loggingSlot(int)
    def _askForConfirmationChanged(self, newState):
        if not self._resetting:
            PrivacySettings.get().setAskForConfirmation(self._action, self._category, newState == Qt.Checked, applyImmediately=False, categoryPolicy=self._getCategoryPolicy())
        
    @loggingSlot(int)
    def _modeChanged(self, newMode, notify=True, resetModel=True):
        self._resetting = True
        if newMode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX, PrivacySettings.POLICY_PEER_EXCEPTION):
            if resetModel:
                # no change notifications, we are just resetting the model
                self._peerModel.itemChanged.disconnect(self._peerDataChanged)
                self._peerModel.setExceptionData(PrivacySettings.get().getExceptions(self._action, self._category, newMode, useModified=True, categoryPolicy=self._getCategoryPolicy()))
                self._peerModel.itemChanged.connect(self._peerDataChanged)
            self._peerList.setVisible(True)
        else:
            self._peerList.setVisible(False)
        
        if newMode == PrivacySettings.POLICY_NOBODY_EX:
            ask = PrivacySettings.get().getAskForConfirmation(self._action, self._category, useModified=True, categoryPolicy=self._getCategoryPolicy())
            self._askForConfirmationBox.setCheckState(Qt.Checked if ask else Qt.Unchecked)
            self._askForConfirmationBox.setVisible(True)
        else:
            self._askForConfirmationBox.setVisible(False)
        self._mode = newMode
        
        self._resetting = False
        if notify:
            PrivacySettings.get().setPolicy(self._action, self._category, self._mode, applyImmediately=False, categoryPolicy=self._getCategoryPolicy())
        
    def setMode(self, newMode):
        self._modeChanged(newMode, notify=False)

    def getCategory(self):
        return self._category

    @loggingSlot(object, object)
    def _privacySettingsChanged(self, pluginName, actionName):
        if pluginName != self._action.getPluginName() or actionName != self._action.getName():
            return
        if self._determineOwnMode:
            newMode = PrivacySettings.get().getPolicy(self._action, self._category, categoryPolicy=self._getCategoryPolicy())
        else:
            newMode = self._mode
        self._modeChanged(newMode, notify=False)