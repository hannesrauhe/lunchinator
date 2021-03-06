from lunchinator.plugin import iface_gui_plugin
from lunchinator import convert_string, get_peers, get_settings, lunchinator_has_gui
from lunchinator.peer_actions import PeerAction
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent,\
    displayNotification, canUseBackgroundQThreads
from lunchinator.privacy.privacy_settings import PrivacySettings
from lunchinator.log.logging_func import loggingFunc
from lunchinator.logging_mutex import loggingMutex
import os
import sys
from time import time
from functools import partial

class _SendMessageAction(PeerAction):
    def getName(self):
        return "Send Message"
    
    def appliesToPeer(self, _peerID, _peerInfo):
        return False
    
    def getMessagePrefix(self):
        return "PM"
    
    def getDefaultPrivacyPolicy(self):
        return PrivacySettings.POLICY_EVERYBODY_EX
    
class _OpenChatAction(PeerAction):
    def __init__(self, sendMessageAction):
        self._sendMessageAction = sendMessageAction
    
    def getName(self):
        return "Open Chat"
    
    def performAction(self, peerID, _peerInfo, _parent):
        self.getPluginObject().openChat(peerID)
        
    def appliesToPeer(self, peerID, peerInfo):
        # this action has no privacy settings, use the ones from send message
        return u"PM_v" in peerInfo and not self._sendMessageAction.getPeerState(peerID) == PrivacySettings.STATE_BLOCKED
    
class _BlockAction(PeerAction):
    def __init__(self, sendMessageAction):
        self._sendMessageAction = sendMessageAction
    
    def getName(self):
        return "Block"
    
    def getDisplayedName(self, peerID):
        policy = self._sendMessageAction.getPrivacyPolicy()
        exceptions = self._sendMessageAction.getExceptions(policy)
        
        if policy == PrivacySettings.POLICY_NOBODY_EX:
            blocked = True
            if peerID in exceptions and exceptions[peerID] == 1:
                blocked = False
            if blocked:
                return "Add to whitelist"
            else:
                return "Remove from whitelist (block)"
        else:
            free = True
            if peerID in exceptions and exceptions[peerID] == 1:
                free = False
            if free:
                return "Block"
            else:
                return "Unblock"
    
    def performAction(self, peerID, _peerInfo, _parent):
        policy = self._sendMessageAction.getPrivacyPolicy()
        if policy not in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
            self.logger.error("Illegal policy for block action: %s", policy)
            return
        
        exceptions = self._sendMessageAction.getExceptions(policy)
        
        newVal = 1
        if peerID in exceptions and exceptions[peerID] == 1:
            newVal = 0
            
        PrivacySettings.get().addException(self._sendMessageAction, None, policy, peerID, newVal)
        
    def appliesToPeer(self, _peerID, peerInfo):
        if not u"PM_v" in peerInfo:
            # no blocking for peers without chat plugin
            return False
        policy = self._sendMessageAction.getPrivacyPolicy()
        return policy in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX)
    
class private_messages(iface_gui_plugin):
    VERSION_INITIAL = 0
    VERSION_CURRENT = VERSION_INITIAL
    
    def __init__(self):
        super(private_messages, self).__init__()
        self.options = [((u"prev_messages", u"Number of previous messages to display"), 5),
                        ((u"enable_markdown", u"Enable Markdown annotations", self._enableMarkdownChanged), False)]
        self.hidden_options = {u"ack_timeout" : 3, # seconds until message delivery is marked as timed out
                               u"next_msgid" : -1} # next free message ID. -1 = not initialized
        
        self._storage = None
        
    def get_displayed_name(self):
        return u"Chat"
    
    def activate(self):
        iface_gui_plugin.activate(self)
        if lunchinator_has_gui():
            self._sendMessageAction = _SendMessageAction()
            self._openChatAction = _OpenChatAction(self._sendMessageAction)
            self._peerActions = [self._openChatAction, _BlockAction(self._sendMessageAction), self._sendMessageAction]
        else:
            self._peerActions = None
        
    def create_widget(self, parent):
        from private_messages.chat_history_view import ChatHistoryWidget
        
        self._lock = loggingMutex("Private Messages", logging=get_settings().get_verbose())
        
        from PyQt4.QtCore import QThread
        from private_messages.chat_messages_handler import ChatMessagesHandler
        if canUseBackgroundQThreads():
            self._messagesThread = QThread()
        else:
            self._messagesThread = None
            
        self._messagesHandler = ChatMessagesHandler(self.logger, self, self.hidden_options[u"ack_timeout"], self.hidden_options[u"next_msgid"])
        if self._messagesThread is not None:
            self._messagesHandler.moveToThread(self._messagesThread)
            self._messagesThread.start()
        
        self._messagesHandler.delayedDelivery.connect(self._delayedDelivery)
        self._messagesHandler.messageIDChanged.connect(self._messageIDChanged)
        self._messagesHandler.displayOwnMessage.connect(self._displayOwnMessage)
        self._messagesHandler.newMessage.connect(self._displayMessage)
        
        self._openChats = {} # mapping peer ID -> ChatDockWidget
        self._history = ChatHistoryWidget(self, parent, self.logger)
        return self._history
    
    def destroy_widget(self):
        for chatWindow in self._openChats.values():
            chatWindow.close()
            
        self.set_hidden_option(u"next_msgid", self._messagesHandler.getNextMessageIDForStorage(), convert=False)
        self._messagesHandler.deactivate()
        if self._messagesThread is not None:
            self._messagesThread.quit()
            self._messagesThread.wait()
            self._messagesThread.deleteLater()
            self._messagesThread = None
        self._messagesHandler = None
        self._storage = None
        self._lock = None
            
        iface_gui_plugin.destroy_widget(self)
        
    def _enableMarkdownChanged(self, _setting, newVal):
        for chatWindow in self._openChats.values():
            chatWindow.getChatWidget().setMarkdownEnabled(newVal)
    
    def extendsInfoDict(self):
        return lunchinator_has_gui()
        
    def extendInfoDict(self, infoDict):
        infoDict[u"PM_v"] = self.VERSION_CURRENT
        
    def get_peer_actions(self):
        return self._peerActions
        
    def process_event(self, cmd, value, _ip, peerInfo, _prep):
        if not cmd.startswith(u"HELO_PM"):
            return
        
        peerID = peerInfo[u"ID"]
        
        subcmd = cmd[7:]
        if subcmd == u"_ACK":
            self._messagesHandler.processAck(peerID, value)
        elif subcmd == u"_TYPING":
            if peerID in self._openChats:
                self._openChats[peerID].getChatWidget().otherIsTyping()
        elif subcmd == u"_CLEARED":
            if peerID in self._openChats:
                self._openChats[peerID].getChatWidget().otherCleared()
        elif subcmd == u"_ERROR":
            self._messagesHandler.processAck(peerID, value, error=True)
        elif subcmd == u"":
            self._messagesHandler.processMessage(peerID, value)
    
    def getStorage(self):
        if self._storage == None:
            with self._lock:
                if self._storage == None:
                    from private_messages.chat_messages_storage import ChatMessagesStorage
                    self._storage = ChatMessagesStorage(self.logger)
        return self._storage
    
    @loggingFunc
    def _displayOwnMessage(self, otherID, msgID, recvTime, msgHTML, msgTime, status, errorMsg):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        errorMsg = convert_string(errorMsg)
        if recvTime == -1:
            recvTime = None
        if not errorMsg:
            errorMsg = None
        
        if otherID in self._openChats:
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().addOwnMessage(msgID, recvTime, msgHTML, msgTime, status, errorMsg)
    
    def _activateChat(self, chatWindow, forceForeground=True):
        chatWindow.showNormal()
        if forceForeground:
            chatWindow.raise_()
            chatWindow.activateWindow()
        return chatWindow
    
    def _openChat(self, myName, otherName, myAvatar, otherAvatar, otherID):
        from private_messages.chat_window import ChatWindow
        newWindow = ChatWindow(None, self.logger, myName, otherName, myAvatar, otherAvatar, otherID, self._sendMessageAction)
        newWindow.getChatWidget().setMarkdownEnabled(self.get_option(u"enable_markdown"))
        
        newWindow.windowClosing.connect(self._chatClosed)
        newWindow.getChatWidget().sendMessage.connect(self._messagesHandler.sendMessage)
        newWindow.getChatWidget().typing.connect(partial(self._messagesHandler.sendTyping, otherID))
        newWindow.getChatWidget().cleared.connect(partial(self._messagesHandler.sendCleared, otherID))
        self._openChats[otherID] = newWindow
        
        prevMessages = self.getStorage().getPreviousMessages(otherID, self.get_option(u"prev_messages"))
        from private_messages.chat_messages_storage import ChatMessagesStorage
        for row in reversed(prevMessages):
            # partner, ID, own, time, status, text
            isOwnMessage = row[ChatMessagesStorage.MSG_IS_OWN_MESSAGE_COL] != 0
            if isOwnMessage:
                newWindow.getChatWidget().addOwnMessage(row[ChatMessagesStorage.MSG_ID_COL],
                                                        row[ChatMessagesStorage.MSG_RECV_TIME_COL],
                                                        row[ChatMessagesStorage.MSG_TEXT_COL],
                                                        row[ChatMessagesStorage.MSG_TIME_COL],
                                                        row[ChatMessagesStorage.MSG_STATUS_COL])
            else:
                newWindow.getChatWidget().addOtherMessage(row[ChatMessagesStorage.MSG_TEXT_COL],
                                                          row[ChatMessagesStorage.MSG_TIME_COL],
                                                          row[ChatMessagesStorage.MSG_RECV_TIME_COL])
        return self._activateChat(newWindow)
        
    @loggingFunc
    def _chatClosed(self, pID):
        pID = convert_string(pID)
        if pID in self._openChats:
            chatWindow = self._openChats[pID]
            chatWindow.deleteLater()
            del self._openChats[pID]
        else:
            self.logger.error("Closed chat window was not maintained: %s", pID)
        
    def getOpenChatAction(self):
        return self._openChatAction
    
    def openChat(self, pID, forceForeground=True):
        pID = convert_string(pID)
        
        if pID in self._openChats:
            return self._activateChat(self._openChats[pID], forceForeground)
        
        otherName = get_peers().getDisplayedPeerName(pID=pID)
        if otherName == None:
            self.logger.error("Could not get info of chat partner %s", pID)
            return
        otherAvatar = get_peers().getPeerAvatarFile(pID=pID)
        
        myName = get_settings().get_user_name()
        myAvatar = get_peers().getPeerAvatarFile(pID=get_settings().get_ID())
        
        return self._openChat(myName, otherName, myAvatar, otherAvatar, pID)

    @loggingFunc
    def _delayedDelivery(self, otherID, msgID, recvTime, error, errorMessage):
        otherID = convert_string(otherID)
        errorMessage = convert_string(errorMessage)
        
        if otherID in self._openChats:
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().delayedDelivery(msgID, recvTime, error, errorMessage)

    @loggingFunc
    def _messageIDChanged(self, otherID, oldID, newID):
        otherID = convert_string(otherID)
        if otherID in self._openChats:
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().messageIDChanged(oldID, newID)

    @loggingFunc
    def _displayMessage(self, otherID, msgHTML, msgTime, msgDict):
        try:
            recvTime = time()
            chatWindow = self.openChat(otherID, False)
            chatWindow.getChatWidget().addOtherMessage(msgHTML, msgTime, recvTime)
            self._messagesHandler.receivedSuccessfully(otherID, msgHTML, msgTime, msgDict, recvTime)
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
                                self.logger,
                                chatWindow.getChatWidget().getOtherIconPath())

if __name__ == '__main__':
    from private_messages.chat_history_view import ChatHistoryModel
    from private_messages.message_item_delegate import MessageItemDelegate
    from PyQt4.QtGui import QTreeView
    
    pm = private_messages()
    
    
    
    def addRow():
        row = [u"",
               0,
               True,
               0,
               0,
               u"sadfklsakdjflkj slkjf laksjd flk jsadlkf jalsd jfl jsalkd jflk jsadl fjlk sajdlkf jlksa jdfl jsadf jl<br>lsakdjflkjsalkdjf lksajdf",
               0]
        
        roq = [u"",
               0,
               False,
               0,
               0,
               u"0 jlksa jdfl jsadf jl<br>lsakdjflkjsalkdjf lksajdf",
               0]
        historyModel = ChatHistoryModel("", [row, roq])
        pm._history._historyTable.setModel(historyModel)
        
    pm.hasConfigOption = lambda _ : False
    pm.run_in_window(addRow)
