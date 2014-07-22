from lunchinator.table_models import TableModelBase
from lunchinator.peer_actions.peer_actions_singleton import PeerActions
from privacy_gui.multiple_categories_view import MultipleCategoriesView
from privacy_gui.single_category_view import SingleCategoryView
from PyQt4.QtGui import QWidget, QVBoxLayout, QTreeView, QFrame, QSplitter
from PyQt4.QtCore import Qt, QVariant
from lunchinator import get_notification_center

class PeerActionsModel(TableModelBase):
    ACTION_ROLE = TableModelBase.SORT_ROLE + 1
    
    def __init__(self):
        columns = [(u"Peer Action", self._updateNameItem)]
        super(PeerActionsModel, self).__init__(None, columns)
        
        self.addPeerActions(PeerActions.get().getAllPeerActions())
    
    def addPeerActions(self, added):
        for pluginName, actions in added.iteritems():
            for action in actions:
                if action.getMessagePrefix():
                    self.appendContentRow(pluginName + action.getName(), action)
                    
    def removePeerActions(self, removed):
        for pluginName, actionNames in removed.iteritems():
            for actionName in actionNames:
                self.externalRowRemoved(pluginName + actionName)
    
    def createItem(self, key, action, column):
        item = TableModelBase.createItem(self, key, action, column)
        item.setData(action, self.ACTION_ROLE)
        return item
            
    def _updateNameItem(self, _actionID, action, item):
        pluginName = None
        if action.getPluginObject() is not None:
            pluginName = action.getPluginObject().get_displayed_name()
        if pluginName is None:
            pluginName = action.getPluginName()
        item.setText("%s: %s" % (pluginName, action.getName()))
        icon = action.getIcon()
        if icon is not None:
            item.setData(QVariant(icon), Qt.DecorationRole)

class PrivacyGUI(QWidget):
    def __init__(self, parent):
        super(PrivacyGUI, self).__init__(parent)
       
        self._actionModel = PeerActionsModel()
        
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
        
    def _peerActionsAdded(self, added):
        self._actionModel.addPeerActions(added)
    
    def _peerActionsRemoved(self, removed):
        self._actionModel.removePeerActions(removed)
        
    def _initActionList(self):  
        self._actionList = QTreeView(self)
        self._actionList.setAlternatingRowColors(True)
        self._actionList.setHeaderHidden(False)
        self._actionList.setItemsExpandable(False)
        self._actionList.setIndentation(0)
        self._actionList.setModel(self._actionModel)
        self._actionList.setSelectionMode(QTreeView.SingleSelection)
        self._actionList.selectionModel().selectionChanged.connect(self._displaySettings)
        
        self._actionList.setObjectName(u"__action_list")
        self._actionList.setFrameShape(QFrame.StyledPanel)
        #if getPlatform() == PLATFORM_MAC:
        #    self._actionList.setStyleSheet("QFrame#__action_list{border-width: 1px; border-top-style: solid; border-right-style: solid; border-bottom-style: none; border-left-style: none; border-color:palette(mid)}");

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
            
    def _displaySettings(self, newSelection, _oldSelection=None):
        self._clearSettingsWidget()
        if len(newSelection.indexes()) > 0:
            index = iter(newSelection.indexes()).next()
            action = index.data(PeerActionsModel.ACTION_ROLE).toPyObject()
            if action.hasCategories():
                self._settingsWidget.layout().addWidget(MultipleCategoriesView(action, self._settingsWidget))
            else:
                self._settingsWidget.layout().addWidget(SingleCategoryView(action, self._settingsWidget))
