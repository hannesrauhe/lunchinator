from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server
import urllib2,sys
    
class peers_table(iface_gui_plugin):
    def __init__(self):
        super(peers_table, self).__init__()
        self.peersTable = None
        
    def smoothScalingChanged(self, _setting, newValue):
        self.webcam.smooth_scaling = newValue
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def do_peers(self):
        print get_server().get_peers()

    def updateTimeoutsInPeersTables(self):
        self.peersProxyModel.setDynamicSortFilter(False)
        self.peersModel.updateTimeouts()
        self.peersProxyModel.setDynamicSortFilter(True)    
        
    def addHostClicked(self, text):
        if get_server().controller != None:
            get_server().controller.addHostClicked(text)        
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import QTimer, Qt
        from peers_table.model import PeersTableModel
        from lunchinator.table_widget import TableWidget
        
        self.peersTable = TableWidget(parent, "Add Host", self.addHostClicked, sortedColumn=2, placeholderText="Enter hostname")
        
        # initialize peers table
        self.peersModel = PeersTableModel(get_server())
        self.peersProxyModel = QSortFilterProxyModel(self.peersTable)
        self.peersProxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.peersProxyModel.setSortRole(PeersTableModel.SORT_ROLE)
        self.peersProxyModel.setDynamicSortFilter(True)
        self.peersProxyModel.setSourceModel(self.peersModel)
        self.peersTable.setModel(self.peersProxyModel)
        
        timeoutTimer = QTimer(self.peersModel)
        timeoutTimer.setInterval(1000)
        timeoutTimer.timeout.connect(self.updateTimeoutsInPeersTables)
        timeoutTimer.start(1000)  
        
        get_server().controller.peerAppendedSignal.connect(self.peersModel.externalRowAppended)
#         get_server().controller.peerUpdatedSignal.connect(self.peersModel.externalRowUpdated)
#         get_server().controller.peerRemovedSignal.connect(self.peersModel.externalRowRemoved)
        
        return self.peersTable
    
    def add_menu(self,menu):
        pass

