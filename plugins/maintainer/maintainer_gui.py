from maintainer.members_widget import MembersWidget
from maintainer.console_widget import ConsoleWidget
from lunchinator import get_peers, get_notification_center, convert_string
from lunchinator.lunch_peers import LunchPeers
from lunchinator.table_models import TableModelBase
from lunchinator.log.logging_slot import loggingSlot

from PyQt4.QtGui import QTreeView, QTabWidget, QSortFilterProxyModel, QSizePolicy,\
    QStandardItem
from PyQt4.QtCore import Qt, QVariant

class ExtendedMembersModel(TableModelBase):
    def __init__(self, dataSource, logger):
        super(ExtendedMembersModel, self).__init__(dataSource, None, logger)
        self.headerNames = []
        if self.dataSource is None:
            return
        for peerID in self.dataSource:
            self.updateModel(peerID, self.dataSource.getPeerInfo(peerID))
    
    def _headerCmp(self, x, y):
        if x == y:
            return 0
        
        if x == LunchPeers.PEER_NAME_KEY:
            return -1
        if y == LunchPeers.PEER_NAME_KEY:
            return 1
        
        if x == LunchPeers.PEER_ID_KEY:
            return -1
        if y == LunchPeers.PEER_ID_KEY:
            return 1 
        
        return cmp(x, y)
        
    @loggingSlot(dict)
    def updateModel(self, peerID, infoDict, update=False, prepend=False):
        # update columns labels
        
        newHeaderNames = sorted(set(self.headerNames).union(infoDict.keys()), cmp=self._headerCmp)
        if newHeaderNames != self.headerNames:
            self.headerNames = newHeaderNames
            for i, headerName in enumerate(newHeaderNames):
                self.setHorizontalHeaderItem(i, QStandardItem(headerName))
            self.updateTable()
            
        if update:
            if peerID in self.keys:
                index = self.keys.index(peerID)
                self.updateRow(peerID, infoDict, index)
        elif prepend:
            self.prependContentRow(peerID, infoDict)
        else:
            self.appendContentRow(peerID, infoDict)
    
    def _dataForKey(self, key):
        return get_peers().getPeerInfo(pID=key)
    
    """ may be called concurrently """
    def callItemInitializer(self, column, key, data, item):
        if data is None:
            return
        headerName = self.headerNames[column]
        text = ""
        if headerName in data:
            text = data[headerName]
        item.setData(QVariant(text), Qt.DisplayRole)
        
    @loggingSlot(object, object)
    def externalRowAppended(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel(key, data)
        
    @loggingSlot(object, object)
    def externalRowUpdated(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel(key, data, update=True)
        
    @loggingSlot(object)
    def externalRowRemoved(self, key):
        TableModelBase.externalRowRemoved(self, key)

class maintainer_gui(QTabWidget):
    LOG_REQUEST_TIMEOUT = 20 # 10 seconds until request is invalid
    def __init__(self, parent, logger):
        super(maintainer_gui, self).__init__(parent)
        self.logger = logger
        self.info_table = None
        
        self.membersWidget = MembersWidget(parent, logger)
        self.addTab(self.membersWidget, "Members")        
        self.addTab(self.create_info_table_widget(self), "Info")
        self.addTab(ConsoleWidget(self, logger), "Log")
        
        self.setCurrentIndex(0)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def update_dropdown_members(self):
        self.membersWidget.update_dropdown_members()
    
    def create_info_table_widget(self, parent):
        self.info_table = QTreeView(parent)
        self.info_table.setSortingEnabled(True)
        self.info_table.setHeaderHidden(False)
        self.info_table.setAlternatingRowColors(True)
        self.info_table.setIndentation(0)
        
        self.info_table_model = ExtendedMembersModel(get_peers(), self.logger)
        proxyModel = QSortFilterProxyModel(self.info_table)
        proxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxyModel.setDynamicSortFilter(True)
        proxyModel.setSourceModel(self.info_table_model)
        
        self.info_table.setModel(proxyModel)
        
        get_notification_center().connectPeerAppended(self.info_table_model.externalRowAppended)
        get_notification_center().connectPeerUpdated(self.info_table_model.externalRowUpdated)
        get_notification_center().connectPeerRemoved(self.info_table_model.externalRowRemoved)
        
        return self.info_table
        
    def destroy_widget(self):
        get_notification_center().disconnectPeerAppended(self.info_table_model.externalRowAppended)
        get_notification_center().disconnectPeerUpdated(self.info_table_model.externalRowUpdated)
        get_notification_center().disconnectPeerRemoved(self.info_table_model.externalRowRemoved)
        
        self.membersWidget.destroy_widget()
    
if __name__ == "__main__":
    from lunchinator.plugin import iface_gui_plugin
    from lunchinator.log import getCoreLogger
    iface_gui_plugin.run_standalone(lambda window : maintainer_gui(window, getCoreLogger()))
    