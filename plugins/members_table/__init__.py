from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server
import urllib2,sys
    
class members_table(iface_gui_plugin):
    def __init__(self):
        super(members_table, self).__init__()
        self.membersTable = None
        
    def smoothScalingChanged(self, _setting, newValue):
        self.webcam.smooth_scaling = newValue
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def do_members(self):
        print get_server().get_members()

    def updateTimeoutsInMembersTables(self):
        self.membersProxyModel.setDynamicSortFilter(False)
        self.membersModel.updateTimeouts()
        self.membersProxyModel.setDynamicSortFilter(True)    
        
    def addHostClicked(self, text):
        if get_server().controller != None:
            get_server().controller.addHostClicked(text)        
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import QTimer, Qt
        from lunchinator.table_models import MembersTableModel
        from lunchinator.table_widget import TableWidget
        
        self.membersTable = TableWidget(parent, "Add Host", self.addHostClicked, sortedColumn=2, placeholderText="Enter hostname")
        
        # initialize members table
        self.membersModel = MembersTableModel(get_server())
        self.membersProxyModel = QSortFilterProxyModel(self.membersTable)
        self.membersProxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.membersProxyModel.setSortRole(MembersTableModel.SORT_ROLE)
        self.membersProxyModel.setDynamicSortFilter(True)
        self.membersProxyModel.setSourceModel(self.membersModel)
        self.membersTable.setModel(self.membersProxyModel)
        
        timeoutTimer = QTimer(self.membersModel)
        timeoutTimer.setInterval(1000)
        timeoutTimer.timeout.connect(self.updateTimeoutsInMembersTables)
        timeoutTimer.start(1000)  
        
        get_server().controller.memberAppendedSignal.connect(self.membersModel.externalRowAppended)
        get_server().controller.memberUpdatedSignal.connect(self.membersModel.externalRowUpdated)
        get_server().controller.memberRemovedSignal.connect(self.membersModel.externalRowRemoved)
        
        return self.membersTable
    
    def add_menu(self,menu):
        pass

