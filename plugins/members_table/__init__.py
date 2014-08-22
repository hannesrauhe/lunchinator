from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_server, get_notification_center, get_peers,\
    convert_string, get_peer_actions
from lunchinator.utilities import msecUntilNextMinute
from functools import partial
from lunchinator.peer_actions import peer_action_utils
from lunchinator.log import loggingFunc
    
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
                # compare by lunch time
                ldata = self.sourceModel().data(left, MembersTableModel.SORT_ROLE)
                rdata = self.sourceModel().data(right, MembersTableModel.SORT_ROLE)
                if ldata != rdata:
                    return super(NameSortProxyModel, self).lessThan(left, right)
                
                # compare by name, case sensitive
                lindex = self.sourceModel().index(left.row(), MembersTableModel.NAME_COL_INDEX)
                rindex = self.sourceModel().index(right.row(), MembersTableModel.NAME_COL_INDEX)
                
                res = super(NameSortProxyModel, self).lessThan(lindex, rindex)
                if res or super(NameSortProxyModel, self).lessThan(rindex, lindex):
                    return res
                
                # compare by name, byte order
                ls = convert_string(self.sourceModel().data(lindex, MembersTableModel.SORT_ROLE).toString())
                rs = convert_string(self.sourceModel().data(rindex, MembersTableModel.SORT_ROLE).toString())
                if ls != rs:
                    return ls < rs
                
                # compare by peer ID 
                return self.sourceModel().keys[left.row()] < self.sourceModel().keys[right.row()]
        
        self.membersTable = TableWidget(parent, "Add Host", self.addHostClicked, sortedColumn=MembersTableModel.LUNCH_TIME_COL_INDEX, placeholderText="Enter hostname")
        self.membersTable.getTable().setContextMenuPolicy(Qt.CustomContextMenu)
        self.membersTable.getTable().customContextMenuRequested.connect(self._showContextMenu)
        
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
        
        get_notification_center().connectMemberAppended(self._updatePeer)
        get_notification_center().connectMemberRemoved(self._updatePeer)
        
        get_notification_center().connectDisplayedPeerNameChanged(self._displayedNameChanged)
        
        self._lunchTimeColumnTimer = QTimer(self.membersModel)
        self._lunchTimeColumnTimer.timeout.connect(self._startSyncedTimer)
        self._lunchTimeColumnTimer.start(msecUntilNextMinute())
        
        return self.membersTable
    
    @loggingFunc
    def _displayedNameChanged(self, peerID, _newName, infoDict):
        self._updatePeer(peerID, infoDict)

    def _updatePeer(self, peerID, infoDict=None):
        peerID = convert_string(peerID)
        if infoDict == None:
            infoDict = get_peers().getPeerInfo(pID=peerID)
        
        if infoDict == None:
            #this happens when a peer that is also a member is removed 
            #-> the peer is not there anymore when the member removed signal arrives
            return
        
        self.membersModel.externalRowUpdated(peerID, infoDict)
    
    @loggingFunc
    def _startSyncedTimer(self):
        self.membersModel.updateLunchTimeColumn()
        self._lunchTimeColumnTimer.timeout.disconnect(self._startSyncedTimer)
        self._lunchTimeColumnTimer.timeout.connect(self.membersModel.updateLunchTimeColumn)
        self._lunchTimeColumnTimer.start(60000)

    @loggingFunc
    def _showContextMenu(self, point):
        from PyQt4.QtGui import QMenu, QCursor
        index = self.membersTable.getTable().indexAt(point)
        index = self.membersProxyModel.mapToSource(index)
        if index != None:
            peerID = self.membersModel.keyAtIndex(index)
            peer_action_utils.showPeerActionsPopup(peerID, lambda _pluginName, _action : True, self.membersTable.getTable())

    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
        get_notification_center().disconnectPeerAppended(self.membersModel.externalRowAppended)
        get_notification_center().disconnectPeerUpdated(self.membersModel.externalRowUpdated)
        get_notification_center().disconnectPeerRemoved(self.membersModel.externalRowRemoved)

        get_notification_center().disconnectMemberAppended(self._updatePeer)
        get_notification_center().disconnectMemberRemoved(self._updatePeer)
        
        get_notification_center().disconnectDisplayedPeerNameChanged(self._displayedNameChanged)
        
        self._lunchTimeColumnTimer.stop()
        self._lunchTimeColumnTimer.deleteLater()

        self.membersTable = None
        self.membersModel = None
        self.membersProxyModel = None
        
    def add_menu(self,menu):
        pass

