from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server
import urllib2,sys
    
class messages_table(iface_gui_plugin):
    def __init__(self):
        super(messages_table, self).__init__()
        self.messagesTable = None
        
    def smoothScalingChanged(self, _setting, newValue):
        self.webcam.smooth_scaling = newValue
    
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def updateSendersInMessagesTable(self):
        self.messagesProxyModel.setDynamicSortFilter(False)
        self.messagesModel.updateSenders()
        self.messagesProxyModel.setDynamicSortFilter(True)
        
    def sendMessageClicked(self, w):
        if get_server().controller != None:
            get_server().controller.sendMessageClicked(None, w)
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from lunchinator.table_widget import TableWidget
        from lunchinator.table_models import MessagesTableModel
        self.messagesTable = TableWidget(parent, "Send Message", self.sendMessageClicked)
        
        # initialize messages table
        self.messagesModel = MessagesTableModel(get_server())
        self.messagesProxyModel = QSortFilterProxyModel(self.messagesTable)
        self.messagesProxyModel.setSortRole(MessagesTableModel.SORT_ROLE)
        self.messagesProxyModel.setDynamicSortFilter(True)
        self.messagesProxyModel.setSourceModel(self.messagesModel)
        self.messagesTable.setModel(self.messagesProxyModel)
        
        get_server().controller.messagePrependedSignal.connect(self.messagesModel.externalRowPrepended)
        get_server().controller.memberAppendedSignal.connect(self.updateSendersInMessagesTable)
        get_server().controller.memberUpdatedSignal.connect(self.updateSendersInMessagesTable)
        get_server().controller.memberRemovedSignal.connect(self.updateSendersInMessagesTable)
        
        return self.messagesTable
    
    def add_menu(self,menu):
        pass

