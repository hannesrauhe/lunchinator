from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, convert_string, log_error, get_peers,\
    get_settings
from lunchinator.peer_actions import PeerAction
from private_messages.chat_history_view import ChatHistoryWidget
from private_messages.chat_messages_handler import ChatMessagesHandler
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent,\
    displayNotification
import os
from lunchinator.logging_mutex import loggingMutex
import sys
    
class _OpenChatAction(PeerAction):
    def getName(self):
        return "Open Chat"
    
    def performAction(self, peerID, _peerInfo):
        self.getPluginObject().openChat(peerID)
        
    def appliesToPeer(self, _peerID, peerInfo):
        return u"PM_v" in peerInfo
    
class private_messages(iface_gui_plugin):
    VERSION_INITIAL = 0
    VERSION_CURRENT = VERSION_INITIAL
    
    def __init__(self):
        super(private_messages, self).__init__()
        self.options = [((u"prev_messages", u"Number of previous messages to display"), 5)]
        self.hidden_options = {u"ack_timeout" : 3} # seconds until message delivery is marked as timed out
        
    def get_displayed_name(self):
        return u"Chat"
        
    def activate(self):
        iface_gui_plugin.activate(self)
        self._peerActions = [_OpenChatAction()]
        
        self._lock = loggingMutex("Private Messages", logging=get_settings().get_verbose())
        self._storage = None
        
        from PyQt4.QtCore import QThread
        self._messagesThread = QThread()
        self._messagesHandler = ChatMessagesHandler(self, self.hidden_options[u"ack_timeout"])
        self._messagesHandler.moveToThread(self._messagesThread)
        self._messagesThread.start()
        
        self._messagesHandler.delayedDelivery.connect(self._delayedDelivery)
        self._messagesHandler.displayOwnMessage.connect(self._displayOwnMessage)
        self._messagesHandler.newMessage.connect(self._displayMessage)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        self._messagesHandler.deactivate()
        self._messagesThread.quit()
        self._messagesThread.wait()
        self._messagesThread.deleteLater()
        self._messagesHandler = None
        self._messagesThread = None
        self._storage = None
        self._lock = None
    
    def create_widget(self, parent):
        self._openChats = {} # mapping peer ID -> ChatDockWidget
        
        w = ChatHistoryWidget(parent)
        return w
    
    def destroy_widget(self):
        self._cleanupThread.stop()
        iface_gui_plugin.destroy_widget(self)
        
    def extendsInfoDict(self):
        return True
        
    def extendInfoDict(self, infoDict):
        infoDict[u"PM_v"] = self.VERSION_CURRENT
        
    def get_peer_actions(self):
        return self._peerActions
        
    def process_event(self, cmd, value, _ip, peerInfo):
        if cmd.startswith(u"HELO_PM_ACK"):
            peerID = peerInfo[u"ID"]
            self._messagesHandler.processAck(peerID, value)
        elif cmd.startswith(u"HELO_PM_ERROR"):
            peerID = peerInfo[u"ID"]
            self._messagesHandler.processAck(peerID, value, error=True)
        elif cmd.startswith(u"HELO_PM"):
            peerID = peerInfo[u"ID"]
            self._messagesHandler.processMessage(peerID, value)
    
    def getStorage(self):
        if self._storage == None:
            with self._lock:
                if self._storage == None:
                    from private_messages.chat_messages_storage import ChatMessagesStorage
                    self._storage = ChatMessagesStorage()
        return self._storage
    
    def _displayOwnMessage(self, otherID, msgID, msgHTML, msgTime, status, errorMsg):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        errorMsg = convert_string(errorMsg)
        if not errorMsg:
            errorMsg = None
        
        if otherID in self._openChats:
            from private_messages.chat_widget import ChatWidget
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().addOwnMessage(msgID, msgHTML, msgTime, status, errorMsg)
    
    def _activateChat(self, chatWindow, forceForeground=True):
        chatWindow.show()
        if forceForeground:
            if getPlatform() == PLATFORM_MAC:
                chatWindow.activateWindow()
            chatWindow.raise_()
        return chatWindow
    
    def _openChat(self, myName, otherName, myAvatar, otherAvatar, otherID):
        from private_messages.chat_window import ChatWindow
        newWindow = ChatWindow(None, myName, otherName, myAvatar, otherAvatar, otherID)
        newWindow.windowClosing.connect(self._chatClosed)
        newWindow.getChatWidget().sendMessage.connect(self._messagesHandler.sendMessage)
        self._openChats[otherID] = newWindow
        
        prevMessages = self.getStorage().getPreviousMessages(otherID, self.get_option(u"prev_messages"))
        for row in reversed(prevMessages):
            # partner, ID, own, time, status, text
            ownMessage = row[2] != 0
            if ownMessage:
                newWindow.getChatWidget().addOwnMessage(row[1], row[5], row[3], row[4], scroll=False)
            else:
                newWindow.getChatWidget().addOtherMessage(row[5], row[3], scroll=False)
        newWindow.getChatWidget().scrollToEnd()
        return self._activateChat(newWindow)
        
    def _chatClosed(self, pID):
        pID = convert_string(pID)
        if pID in self._openChats:
            chatWindow = self._openChats[pID]
            chatWindow.deleteLater()
            del self._openChats[pID]
        else:
            log_error("Closed chat window was not maintained:", pID)
        
    def openChat(self, pID, forceForeground=False):
        pID = convert_string(pID)
        
        if pID in self._openChats:
            return self._activateChat(self._openChats[pID], forceForeground)
        
        otherName = get_peers().getDisplayedPeerName(pID=pID)
        if otherName == None:
            log_error("Could not get info of chat partner", pID)
            return
        otherAvatar = get_peers().getPeerAvatarFile(pID=pID)
        
        myName = get_settings().get_user_name()
        myAvatar = get_peers().getPeerAvatarFile(pID=get_settings().get_ID())
        
        return self._openChat(myName, otherName, myAvatar, otherAvatar, pID)

    def _delayedDelivery(self, otherID, msgID, error, errorMessage):
        otherID = convert_string(otherID)
        errorMessage = convert_string(errorMessage)
        
        if otherID in self._openChats:
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().delayedDelivery(msgID, error, errorMessage)

    def _displayMessage(self, otherID, msgHTML, msgTime, msgDict):
        try:
            chatWindow = self.openChat(otherID, False)
            chatWindow.getChatWidget().addOtherMessage(msgHTML, msgTime)
            self._messagesHandler.receivedSuccessfully(otherID, msgHTML, msgTime, msgDict)
        except:
            excType, excValue, _tb = sys.exc_info()
            errorMsg = u"Error processing message (%s: %s)" % (unicode(excType.__name__), unicode(excValue))
            self._messagesHandler.errorReceivingMessage(otherID, msgDict, errorMsg)
        
        if not chatWindow.isActiveWindow():
            from PyQt4.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setHtml(msgHTML)
            displayNotification(chatWindow.getChatWidget().getOtherName(),
                                convert_string(doc.toPlainText()),
                                chatWindow.getChatWidget().getOtherIconPath())

if __name__ == '__main__':
    pm = private_messages()
    pm.run_in_window()
