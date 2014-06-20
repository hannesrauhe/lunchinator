from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server,\
    get_notification_center, log_debug, get_peers, log_error, convert_string,\
    log_info, log_warning
import urllib2, sys, os, json
from datetime import datetime, timedelta
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent,\
    displayNotification
from time import time
from lunchinator.peer_actions import PeerAction
from private_messages.chat_messages_storage import ChatMessagesStorage
from private_messages.chat_history_view import ChatHistoryWidget
    
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
        self._ackTimeout = self.hidden_options[u"ack_timeout"]
        self._peerActions = [_OpenChatAction()]
        self._waitingForAck = {} # message ID : (otherID, time, message)
        self._nextMessageID = None
        self._storage = None
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtCore import QTimer
        self._cleanupTimer = QTimer(parent)
        self._cleanupTimer.timeout.connect(self._cleanup)
        self._cleanupTimer.start(2000)
        
        self._openChats = {} # mapping peer ID -> ChatDockWidget
        
        w = ChatHistoryWidget(parent)
        return w
    
    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
    def extendsInfoDict(self):
        return True
        
    def extendInfoDict(self, infoDict):
        infoDict[u"PM_v"] = self.VERSION_CURRENT
        
    def get_peer_actions(self):
        return self._peerActions
        
    def _getStorage(self):
        if self._storage == None:
            self._storage = ChatMessagesStorage()
            self._nextMessageID = self._storage.getNextMessageID()
        return self._storage
        
    def _getNextMessageID(self):
        if self._nextMessageID == None:
            self._getStorage()
        return self._nextMessageID
        
    def _cleanup(self):
        curTime = time()
        for msgID, tup in dict(self._waitingForAck).iteritems():
            otherID, msgTime, msgHTML = tup
            if curTime - msgTime > self._ackTimeout:
                self._deliveryTimedOut(otherID, msgID, msgHTML)
                del self._waitingForAck[msgID]
    
    def _deliveryTimedOut(self, otherID, msgID, msgHTML):
        from private_messages.chat_messages_model import ChatMessagesModel
        self._displayOwnMessage(otherID, msgID, msgHTML, ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED)
        
    def _checkDelayedAck(self, otherID, msgID):
        from private_messages.chat_messages_model import ChatMessagesModel
        currentState = self._getStorage().getMessageState(msgID)
        if currentState == ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED:
            try:
                self._getStorage().updateMessageState(msgID, ChatMessagesModel.MESSAGE_STATE_OK)
            except:
                log_exception("Error updating message state")
            
            if otherID in self._openChats:
                from private_messages.chat_widget import ChatWidget
                chatWindow = self._openChats[otherID]
                chatWindow.getChatWidget().delayedDelivery(msgID)
            
            return True
        return False
        
    def _openChatWithMyself(self):
        myID = get_settings().get_ID()
        self.openChat(myID)
    
    def process_event(self, cmd, value, _ip, peerInfo):
        if cmd.startswith(u"HELO_PM_ACK"):
            peerID = peerInfo[u"ID"]
            self._processAck(peerID, value)
        elif cmd.startswith(u"HELO_PM_ERROR"):
            peerID = peerInfo[u"ID"]
            self._processAck(peerID, value, error=True)
        elif cmd.startswith(u"HELO_PM"):
            peerID = peerInfo[u"ID"]
            self._processMessage(peerID, value)
    
    def _processAck(self, ackPeerID, valueJSON, error=False):
        try:
            answerDict = json.loads(valueJSON)
        except:
            log_error("Error reading ACK message:", valueJSON)
            return
        
        if not u"id" in answerDict:
            log_error("No message ID in ACK message:", valueJSON)
            return
        
        msgID = answerDict[u"id"]
        if not msgID in self._waitingForAck:
            if self._checkDelayedAck(ackPeerID, msgID):
                log_debug("Delayed delivery of message", msgID, "to", ackPeerID)
                return
            log_warning("Received ACK for message ID '%s' that I was not waiting for." % msgID)
            return
        
        otherID, _time, msgHTML = self._waitingForAck.pop(msgID)
        if otherID != ackPeerID:
            log_warning("Received ACK from different peer ID than the message was sent to ('%s' != '%s')" % (otherID, ackPeerID))
            return
        
        errorMsg = None
        if error:
            if u"err" in answerDict:
                errorMsg = answerDict[u"err"]
                log_warning("Message '%s' could not be processed by '%s': %s" % (msgID, otherID, errorMsg))
            else:
                log_warning("Message '%s' could not be processed by '%s'" % (msgID, otherID))
                
        from private_messages.chat_messages_model import ChatMessagesModel
        self._displayOwnMessage(otherID, msgID, msgHTML, ChatMessagesModel.MESSAGE_STATE_ERROR if error else ChatMessagesModel.MESSAGE_STATE_OK, errorMsg)
        
    def _displayOwnMessage(self, otherID, msgID, msgHTML, status, errorMsg=None):
        msgTime = time()
        if otherID in self._openChats:
            from private_messages.chat_widget import ChatWidget
            chatWindow = self._openChats[otherID]
            # TODO add message time to model
            chatWindow.getChatWidget().addOwnMessage(msgID, msgHTML, status, errorMsg)
        
        try:
            self._getStorage().addOwnMessage(msgID, otherID, msgTime, status, msgHTML)
        except:
            log_exception("Error storing own message")
    
    def _processMessage(self, otherID, msgDictJSON):
        try:
            msgDict = json.loads(msgDictJSON)
        except:
            self._sendAnswer(otherID, {}, "Error loading message: %s" % msgDictJSON)
            return
        
        if not u"data" in msgDict:
            self._sendAnswer(otherID, msgDict, u"Message does not contain data:%s" % msgDict)
            return
        
        if u"format" in msgDict:
            if msgDict[u"format"] == u"html":
                msgHTML = msgDict[u"data"]
            else:
                self._sendAnswer(otherID, msgDict, u"Unknown message format: %s" % msgDict[u"format"])
                return
        else:
            log_info("Message without format. Assuming plain text or HTML.")
            msgHTML = msgDict[u"data"]
        
        chatWindow = self.openChat(otherID, forceForeground=False)
        msgTime = time()
        
        # TODO add message time to model
        chatWindow.getChatWidget().addOtherMessage(msgHTML)
        if not chatWindow.isActiveWindow():
            from PyQt4.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setHtml(msgHTML)
            displayNotification(chatWindow.getChatWidget().getOtherName(),
                                convert_string(doc.toPlainText()),
                                chatWindow.getChatWidget().getOtherIconPath())
        
        if u"id" in msgDict and msgDict[u"id"] != None:
            self._sendAnswer(otherID, msgDict)
            try:
                self._getStorage().addOtherMessage(msgDict[u"id"], otherID, msgTime, msgHTML)
            except:
                log_exception("Error storing partner message")
        else:
            log_warning("Message has no ID, cannot store or send answer.")
        
    def _sendAnswer(self, otherID, msgDict, errorMsg=None):
        if u"id" not in msgDict:
            if errorMsg:
                log_error(errorMsg)
            log_debug("Message has no ID, cannot send answer.")
            return
        
        answerDict = {u"id": msgDict[u"id"]}
        if not errorMsg:
            get_server().call("HELO_PM_ACK " + json.dumps(answerDict), peerIDs=[otherID])
        else:
            answerDict[u"err"] = errorMsg 
            log_error(errorMsg)
            get_server().call("HELO_PM_ERROR " + json.dumps(answerDict), peerIDs=[otherID])  
    
    def _sendMessage(self, otherID, msgHTML):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        
        msgDict = {u"id": self._getNextMessageID(),
                   u"format": u"html",
                   u"data": msgHTML}
        
        try:
            msgDictJSON = json.dumps(msgDict)
        except:
            log_exception("Error serializing private message:", msgDict)
            return
        
        get_server().call("HELO_PM " + msgDictJSON, peerIDs=[otherID])
        self._waitingForAck[self._getNextMessageID()] = (otherID, time(), msgHTML)
        self._nextMessageID += 1
    
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
        newWindow.getChatWidget().sendMessage.connect(self._sendMessage)
        self._openChats[otherID] = newWindow
        
        prevMessages = self._getStorage().getPreviousMessages(otherID, self.get_option(u"prev_messages"))
        for row in reversed(prevMessages):
            # partner, ID, own, time, status, text
            ownMessage = row[2] != 0
            if ownMessage:
                newWindow.getChatWidget().addOwnMessage(row[1], row[5], row[4], scroll=False)
            else:
                newWindow.getChatWidget().addOtherMessage(row[5], scroll=False)
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
        if pID in self._openChats:
            return self._activateChat(self._openChats[pID], forceForeground)
        
        otherName = get_peers().getDisplayedPeerName(pID=pID)
        if otherName == None:
            log_error("Could not get info of chat partner", pID)
            return
        otherAvatar = get_peers().getPeerAvatarFile(pID=pID)
        if not otherAvatar:
            otherAvatar = get_settings().get_resource("images", "lunchinator.png")
        
        myName = get_settings().get_user_name()
        myAvatar = get_settings().get_avatar_file()
        if not os.path.exists(myAvatar):
            myAvatar = get_settings().get_resource("images", "me.png")
        
        return self._openChat(myName, otherName, myAvatar, otherAvatar, pID)

if __name__ == '__main__':
    pm = private_messages()
    pm.run_in_window()
