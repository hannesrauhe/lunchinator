from lunchinator.table_models import TableModelBase
from lunchinator.peer_actions.peer_actions_singleton import PeerActions
from privacy_gui.multiple_categories_view import MultipleCategoriesView
from privacy_gui.single_category_view import SingleCategoryView
from PyQt4.QtGui import QWidget, QVBoxLayout, QTreeView, QFrame, QSplitter,\
    QItemSelection, QStandardItemModel, QStandardItem
from PyQt4.QtCore import Qt, QVariant
from lunchinator import get_notification_center
from lunchinator.log.logging_slot import loggingSlot

class PeerActionsModel(QStandardItemModel):
    ACTION_ROLE = TableModelBase.SORT_ROLE + 1
    
    def __init__(self, parent, logger):
        super(PeerActionsModel, self).__init__(parent)
        self.logger = logger
        self._pluginToRow = {}
        self.setHorizontalHeaderLabels([u"Peer Actions"])
        self.addPeerActions(PeerActions.get().getAllPeerActions())
    
    def _createPluginItem(self, action):
        item = QStandardItem()
        item.setEditable(False)
        pluginName = None
        if action.getPluginObject() is not None:
            pluginName = action.getPluginObject().get_displayed_name()
        if pluginName is None:
            pluginName = action.getPluginName()
        item.setText(pluginName)
        #icon = action.getPluginObject().getIcon()
        #if icon is not None:
        #    item.setData(QVariant(icon), Qt.DecorationRole)
        return item
    
    def _createActionItem(self, action):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(action, self.ACTION_ROLE)
        item.setText(action.getName())
        icon = action.getIcon()
        if icon is not None:
            item.setData(QVariant(icon), Qt.DecorationRole)
        return item
            
    def addPeerActions(self, added):
        for _pluginName, actions in added.iteritems():
            hasPrivacySettings = any(action.hasPrivacySettings() for action in actions)
            if not hasPrivacySettings:
                continue
            pluginItem = self._createPluginItem(actions[0])
            for action in actions:
                if action.hasPrivacySettings():
                    actionItem = self._createActionItem(action)
                    
                    pluginItem.appendRow([actionItem])
            self.appendRow([pluginItem])
                    
    def removePeerActions(self, removed):
        for pluginName in removed:
            row = self._pluginToRow.get(pluginName, None)
            if row is not None:
                self.removeRow(row)

class PrivacyGUI(QWidget):
    def __init__(self, parent, logger):
        super(PrivacyGUI, self).__init__(parent)
       
        self.logger = logger
        self._actionModel = PeerActionsModel(self, self.logger)
        
        self._initActionList()
        self._initSettingsWidget()
        mainWidget = self._initMainWidget()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(mainWidget)
        
        get_notification_center().connectPeerActionsAdded(self._peerActionsAdded)
        get_notification_center().connectPeerActionsRemoved(self._peerActionsRemoved)
        
    def finish(self):
        get_notification_center().disconnectPeerActionsAdded(self._peerActionsAdded)
        get_notification_center().disconnectPeerActionsRemoved(self._peerActionsRemoved)
        self._clearSettingsWidget()
        
    @loggingSlot(object)
    def _peerActionsAdded(self, added):
        self._actionModel.addPeerActions(added)
    
    @loggingSlot(object)
    def _peerActionsRemoved(self, removed):
        self._actionModel.removePeerActions(removed)
        
    def _initActionList(self):  
        self._actionList = QTreeView(self)
        self._actionList.setAlternatingRowColors(True)
        self._actionList.setHeaderHidden(False)
        self._actionList.setItemsExpandable(True)
        self._actionList.setIndentation(15)
        self._actionList.setModel(self._actionModel)
        self._actionList.expandAll()
        self._actionList.setSelectionMode(QTreeView.SingleSelection)
        self._actionList.selectionModel().selectionChanged.connect(self._displaySettings)
        
        self._actionList.setObjectName(u"__action_list")
        self._actionList.setFrameShape(QFrame.StyledPanel)

    def _initSettingsWidget(self):        
        self._settingsWidget = QWidget(self)
        settingsLayout = QVBoxLayout(self._settingsWidget)
        settingsLayout.setContentsMargins(0, 0, 0, 0)

    def _initMainWidget(self):
        split = QSplitter(Qt.Horizontal, self)
        split.addWidget(self._actionList)
        split.addWidget(self._settingsWidget)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        return split
    
    def hideEvent(self, event):
        self._clearSettingsWidget()
        return QWidget.hideEvent(self, event)
    
    def showEvent(self, event):
        self._displaySettings(self._actionList.selectionModel().selection())
        return QWidget.showEvent(self, event)
    
    def _clearSettingsWidget(self):
        layout = self._settingsWidget.layout()
        
        child = layout.takeAt(0)
        while child != None:
            child.widget().finish()
            child.widget().deleteLater()
            child = layout.takeAt(0)
            
    @loggingSlot(QItemSelection, QItemSelection)
    def _displaySettings(self, newSelection, _oldSelection=None):
        self._clearSettingsWidget()
        if len(newSelection.indexes()) > 0:
            index = iter(newSelection.indexes()).next()
            action = index.data(PeerActionsModel.ACTION_ROLE).toPyObject()
            if action is None:
                return # root item
            if action.hasCategories():
                self._settingsWidget.layout().addWidget(MultipleCategoriesView(action, self._settingsWidget, self.logger))
            else:
                self._settingsWidget.layout().addWidget(SingleCategoryView(action, self._settingsWidget, self.logger))
