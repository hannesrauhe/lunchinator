from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server,\
    get_notification_center
import urllib2,sys
    
class messages_table(iface_gui_plugin):
    def __init__(self):
        super(messages_table, self).__init__()
        self.messagesTable = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def updateSendersInMessagesTable(self):
        self.messagesModel.updateSenders()
        
    def sendMessageClicked(self, text):
        if get_server().controller != None:
            get_server().controller.sendMessageClicked(None, text)
        
    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
        get_notification_center().disconnectMessagePrepended(self.messagesModel.externalRowPrepended)
        get_notification_center().disconnectPeerAppended(self.updateSendersInMessagesTable)
        get_notification_center().disconnectPeerUpdated(self.updateSendersInMessagesTable)
        get_notification_center().disconnectPeerRemoved(self.updateSendersInMessagesTable)
        
        self.messagesModel = None
        self.messagesTable = None
        
    def create_widget(self, parent):
        from PyQt4.QtGui import QSortFilterProxyModel
        from PyQt4.QtCore import Qt
        from lunchinator.table_widget import TableWidget
        from messages_table.messages_table_model import MessagesTableModel
        
        self.messagesTable = TableWidget(parent, "Send Message", self.sendMessageClicked, placeholderText="Enter a message", sortingEnabled=False)
        
        # initialize messages table
        self.messagesModel = MessagesTableModel(parent)
        self.messagesTable.setModel(self.messagesModel)
        self.messagesTable.setColumnWidth(0, 120)
        self.messagesTable.setColumnWidth(1, 90)
        
        get_notification_center().connectMessagePrepended(self.messagesModel.messagePrepended)
        get_notification_center().connectPeerAppended(self.updateSendersInMessagesTable)
        get_notification_center().connectPeerUpdated(self.updateSendersInMessagesTable)
        get_notification_center().connectPeerRemoved(self.updateSendersInMessagesTable)
        
        return self.messagesTable
    
    def add_menu(self,menu):
        pass
