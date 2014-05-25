from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, get_notification_center, get_peers
from lunchinator.utilities import msecUntilNextMinute
    
class members_table(iface_gui_plugin):
    def __init__(self):
        super(members_table, self).__init__()
        self.membersTable = None
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Peers"
        
    def addHostClicked(self, text):
        if get_server().controller != None:
            get_server().controller.addHostClicked(text)        
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import QTimer, Qt
        from members_table.members_table_model import MembersTableModel
        from lunchinator.table_widget import TableWidget
        
        class NameSortProxyModel(QSortFilterProxyModel):
            def lessThan(self, left, right):
                ldata = self.sourceModel().data(left, MembersTableModel.SORT_ROLE)
                rdata = self.sourceModel().data(right, MembersTableModel.SORT_ROLE)
                if ldata == rdata:
                    lindex = self.sourceModel().index(left.row(), 0)
                    rindex = self.sourceModel().index(right.row(), 0)
                    
                    return super(NameSortProxyModel, self).lessThan(lindex, rindex)
                
                return super(NameSortProxyModel, self).lessThan(left, right)
        
        self.membersTable = TableWidget(parent, "Add Host", self.addHostClicked, sortedColumn=MembersTableModel.LUNCH_TIME_COL_INDEX, placeholderText="Enter hostname")
        
        # initialize members table
        self.membersModel = MembersTableModel(get_peers())
        self.membersProxyModel = NameSortProxyModel(self.membersTable)
        self.membersProxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.membersProxyModel.setSortRole(MembersTableModel.SORT_ROLE)
        self.membersProxyModel.setDynamicSortFilter(True)
        self.membersProxyModel.setSourceModel(self.membersModel)
        self.membersTable.setModel(self.membersProxyModel)
        
        self.membersTable.setColumnWidth(MembersTableModel.NAME_COL_INDEX, 150)
        self.membersTable.setColumnWidth(MembersTableModel.GROUP_COL_INDEX, 150)
        
        get_notification_center().connectPeerAppended(self.membersModel.externalRowAppended)
        get_notification_center().connectPeerUpdated(self.membersModel.externalRowUpdated)
        get_notification_center().connectPeerRemoved(self.membersModel.externalRowRemoved)
        
        self._lunchTimeColumnTimer = QTimer(self.membersModel)
        self._lunchTimeColumnTimer.timeout.connect(self._startSyncedTimer)
        self._lunchTimeColumnTimer.start(msecUntilNextMinute)
        
        return self.membersTable
    
    def _startSyncedTimer(self):
        self.membersModel.updateLunchTimeColumn()
        self._lunchTimeColumnTimer.timeout.disconnect(self._startSyncedTimer)
        self._lunchTimeColumnTimer.timeout.connect(self.membersModel.updateLunchTimeColumn)
        self._lunchTimeColumnTimer.start(60000)

    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
        get_notification_center().disconnectPeerAppended(self.membersModel.externalRowAppended)
        get_notification_center().disconnectPeerUpdated(self.membersModel.externalRowUpdated)
        get_notification_center().disconnectPeerRemoved(self.membersModel.externalRowRemoved)

        self._lunchTimeColumnTimer.stop()
        self._lunchTimeColumnTimer.deleteLater()

        self.membersTable = None
        self.membersModel = None
        self.membersProxyModel = None
        
    def add_menu(self,menu):
        pass

