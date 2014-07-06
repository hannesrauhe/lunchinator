from lunchinator import get_peers, get_notification_center, convert_string
from lunchinator.table_models import TableModelBase
from PyQt4.QtGui import QTreeView, QTabWidget, QSortFilterProxyModel, QSizePolicy,\
    QStandardItem
from PyQt4.QtCore import Qt, pyqtSlot, QVariant
from maintainer.members_widget import MembersWidget

class ExtendedMembersModel(TableModelBase):
    def __init__(self, dataSource):
        super(ExtendedMembersModel, self).__init__(dataSource, None)
        self.headerNames = []
        for peerID in self.dataSource:
            self.updateModel(peerID, self.dataSource.getPeerInfo(peerID))
    
    def _headerCmp(self, x, y):
        x = x.lower()
        y = y.lower()
        
        if x == y:
            return 0
        
        if x == u"name":
            return -1
        if y == u"name":
            return 1
        
        if x == u"id":
            return -1
        if y == u"id":
            return 1 
        
        return cmp(x, y)
        
    @pyqtSlot(dict)
    def updateModel(self, peerID, infoDict, update=False, prepend=False):
        # update columns labels
        
        newHeaderNames = sorted(set(self.headerNames).union(infoDict.keys()), cmp=self._headerCmp)
        if newHeaderNames != self.headerNames:
            self.headerNames = newHeaderNames
            for i, headerName in enumerate(newHeaderNames):
                self.setHorizontalHeaderItem(i, QStandardItem(headerName))
            
        if update:
            if peerID in self.keys:
                index = self.keys.index(peerID)
                self.updateRow(peerID, infoDict, index)
        elif prepend:
            self.prependContentRow(peerID, infoDict)
        else:
            self.appendContentRow(peerID, infoDict)
    
    """ may be called concurrently """
    def callItemInitializer(self, column, key, data, item):
        headerName = self.headerNames[column]
        text = ""
        if headerName in data:
            text = data[headerName]
        item.setData(QVariant(text), Qt.DisplayRole)
        
    def externalRowAppended(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel(key, data)
        
    def externalRowPrepended(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel(key, data, prepend=True)
    
    def externalRowUpdated(self, key, data):
        key = convert_string(key)
        data = self._checkDict(data)
        self.updateModel(key, data, update=True)
        
    def externalRowRemoved(self, key):
        TableModelBase.externalRowRemoved(self, key)

class maintainer_gui(QTabWidget):
    LOG_REQUEST_TIMEOUT = 20 # 10 seconds until request is invalid
    def __init__(self,parent):
        super(maintainer_gui, self).__init__(parent)
        self.info_table = None
        self.visible = False
        
        self.membersWidget = MembersWidget(parent) 
        self.addTab(self.membersWidget, "Members")        
        self.addTab(self.create_info_table_widget(self), "Info")
        
        self.setCurrentIndex(0)
        self.visible = True
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def update_dropdown_members(self):
        self.membersWidget.update_dropdown_members()
    
    def create_info_table_widget(self, parent):
        self.info_table = QTreeView(parent)
        self.info_table.setSortingEnabled(True)
        self.info_table.setHeaderHidden(False)
        self.info_table.setAlternatingRowColors(True)
        self.info_table.setIndentation(0)
        
        self.info_table_model = ExtendedMembersModel(get_peers())
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
        self.visible = False
    
if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : maintainer_gui(window))
    