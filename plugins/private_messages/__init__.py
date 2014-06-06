from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server,\
    get_notification_center, log_debug, get_peers, log_error, convert_string,\
    log_info, log_warning
import urllib2, sys, os, json
from datetime import datetime, timedelta
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent
from time import time
    
class private_messages(iface_gui_plugin):
    ACK_TIMEOUT = 3 # seconds until message delivery is marked as timed out
    _nextMessageID = 0
    
    def __init__(self):
        super(private_messages, self).__init__()
        
    def get_displayed_name(self):
        return u"Chat"
        
    def activate(self):
        iface_gui_plugin.activate(self)
        self._waitingForAck = {} # message ID : (otherID, time, message)
        # TODO load _nextMessageID
        
    def deactivate(self):
        # TODO store _nextMessageID
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtCore import QTimer
        self._cleanupTimer = QTimer(parent)
        self._cleanupTimer.timeout.connect(self._cleanup)
        self._cleanupTimer.start(2000)
        
        # TODO use this to browse messages history later
        from PyQt4.QtGui import QWidget, QVBoxLayout, QPushButton
        # TODO remove this
        self._openChats = {} # mapping peer ID -> ChatDockWidget
        self._openChat("Corny", "Other", get_settings().get_resource("images", "me.png"), get_settings().get_resource("images", "lunchinator.png"), "otherID")
        
        w = QWidget(parent)
        l = QVBoxLayout(w)
        b = QPushButton("Open Chat")
        b.clicked.connect(self._openChatWithMyself)
        l.addWidget(b)
        return w
    
    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
    def _cleanup(self):
        curTime = time()
        for msgID, tup in dict(self._waitingForAck).iteritems():
            otherID, msgTime, msgHTML = tup
            if curTime - msgTime > self.ACK_TIMEOUT:
                self._deliveryTimedOut(otherID, msgID, msgHTML)
                del self._waitingForAck[msgID]
    
    def _deliveryTimedOut(self, otherID, msgID, msgHTML):
        from private_messages.chat_messages_model import ChatMessagesModel
        self._displayOwnMessage(otherID, msgID, msgHTML, ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED)
        
    def _checkDelayedAck(self, otherID, msgID):
        # TODO check storage first
        if otherID in self._openChats:
            from private_messages.chat_widget import ChatWidget
            chatWindow = self._openChats[otherID]
            return chatWindow.getChatWidget().delayedDelivery(msgID)
        return False
        
    def _openChatWithMyself(self):
        myID = get_settings().get_ID()
        self.openChat(myID)
    
    def process_event(self, cmd, value, _ip, peerInfo):
        peerID = peerInfo[u"ID"]
        if cmd.startswith(u"HELO_PM_ACK"):
            self._processAck(peerID, value)
        elif cmd.startswith(u"HELO_PM_ERROR"):
            self._processAck(peerID, value, error=True)
        elif cmd.startswith(u"HELO_PM"):
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
        if otherID in self._openChats:
            from private_messages.chat_widget import ChatWidget
            chatWindow = self._openChats[otherID]
            chatWindow.getChatWidget().addOwnMessage(msgID, msgHTML, status, errorMsg)
            # TODO store message
        else:
            # TODO probably store somewhere that the message was processed
            pass
    
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
        
        chatWindow = self.openChat(otherID)
        chatWindow.getChatWidget().addOtherMessage(msgHTML)
        self._sendAnswer(otherID, msgDict)
        # TODO store message
        
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
        
        msgDict = {u"id": self._nextMessageID,
                   u"format": u"html",
                   u"data": msgHTML}
        
        try:
            msgDictJSON = json.dumps(msgDict)
        except:
            log_exception("Error serializing private message:", msgDict)
            return
        
        get_server().call("HELO_PM " + msgDictJSON, peerIDs=[otherID])
        self._waitingForAck[self._nextMessageID] = (otherID, time(), msgHTML)
        self._nextMessageID += 1
    
    def _activateChat(self, chatWindow):
        chatWindow.show()
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
        return self._activateChat(newWindow)
        
    def _chatClosed(self, pID):
        pID = convert_string(pID)
        if pID in self._openChats:
            chatWindow = self._openChats[pID]
            chatWindow.deleteLater()
            del self._openChats[pID]
        else:
            log_error("Closed chat window was not maintained:", pID)
        
    def openChat(self, pID):
        if pID in self._openChats:
            return self._activateChat(self._openChats[pID])
        
        otherName = get_peers().getPeerName(pID=pID)
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
