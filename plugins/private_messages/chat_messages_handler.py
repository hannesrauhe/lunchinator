from private_messages.chat_messages_model import ChatMessagesModel
from private_messages.chat_messages_storage import InconsistentIDError,\
    ChatMessagesStorage
from lunchinator import convert_string, get_server, get_peers,\
    get_notification_center, get_settings
from lunchinator.log.logging_slot import loggingSlot
from PyQt4.QtCore import pyqtSignal, QTimer, QObject
import json
from time import time
        
class ChatMessagesHandler(QObject):
    # other ID, message ID, receive time, HTML, time, state, error message
    displayOwnMessage = pyqtSignal(object, int, float, object, float, int, object)
    # other ID, message ID, receive time, error, error message
    delayedDelivery = pyqtSignal(object, int, float, bool, object)
    # other ID, old ID, new ID
    messageIDChanged = pyqtSignal(object, int, int)
    # otherID, msgHTML, msgTime
    newMessage = pyqtSignal(object, object, float, object)
    
    # private signals
    _processAck = pyqtSignal(object, object, bool)
    _processMessage = pyqtSignal(object, object)
    _receivedSuccessfully = pyqtSignal(object, object, float, object, float)
    _errorReceivingMessage = pyqtSignal(object, object, object)
    
    def __init__(self, logger, delegate, ackTimeout, nextMsgID):
        super(ChatMessagesHandler, self).__init__()
        
        self.logger = logger
        self._delegate = delegate
        self._ackTimeout = ackTimeout
        self._waitingForAck = {} # message ID : (otherID, time, message, isResend)
        self._hasUndelivered = True # just assume until proven otherwise
        
        nextIDFromDB = self._getStorage().getLastSentMessageID() + 1
        self._nextMessageID = max(nextMsgID, nextIDFromDB)
        
        self._cleanupTimer = QTimer(self)
        self._cleanupTimer.timeout.connect(self._cleanup)
        self._cleanupTimer.start(2000)
        
        self._processAck.connect(self._processAckSlot)
        self._processMessage.connect(self._processMessageSlot)
        self._receivedSuccessfully.connect(self._receivedSuccessfullySlot)
        self._errorReceivingMessage.connect(self._errorReceivingMessageSlot)
        
        get_notification_center().connectPeerAppended(self._peerAppended)
        
    def deactivate(self):
        self._cleanupTimer.stop()
        
    def _getStorage(self):
        return self._delegate.getStorage()
        
    def _getNextMessageID(self):
        nextID = self._nextMessageID
        self._nextMessageID += 1
        return nextID
    
    def getNextMessageIDForStorage(self):
        return self._nextMessageID
        
    @loggingSlot(object, object)
    def _peerAppended(self, peerID, _infoDict):
        peerID = convert_string(peerID)
        self._resendUndeliveredMessages(curTime=None, partner=peerID, force=True)
        
    def _resendUndeliveredMessages(self, curTime, partner=None, force=False):
        if not partner and not self._hasUndelivered:
            return
        
        undelivered = self._getStorage().getRecentUndeliveredMessages(partner)
        if not partner and not undelivered:
            self._hasUndelivered=False
        
        for msgTuple in undelivered:
            msgTime = msgTuple[ChatMessagesStorage.MSG_TIME_COL]
            if not force:
                timeout = int(curTime - msgTime)
                if timeout > get_settings().get_peer_timeout():
                    continue
                
            msgID = msgTuple[ChatMessagesStorage.MSG_ID_COL]
            if msgID in self._waitingForAck:
                # already resent and waiting for ACK
                continue
            
            # check if partner is online
            otherID = msgTuple[ChatMessagesStorage.MSG_PARTNER_COL]
            if get_peers().isPeerID(pID=otherID):
                self.logger.debug("Resending undelivered message %d to peer '%s'", msgID, otherID)
                # partner is online, resend message
                msgHTML = msgTuple[ChatMessagesStorage.MSG_TEXT_COL]
                self.sendMessage(otherID, msgHTML, msgID, msgTime)
    
    @loggingSlot()
    def _cleanup(self):
        curTime = time()
        
        self._resendUndeliveredMessages(curTime)
        
        waitingForAck = dict(self._waitingForAck)
        
        removedIDs = []
        for msgID, tup in waitingForAck.iteritems():
            otherID, msgTime, msgHTML, isResend = tup
            if curTime - msgTime > self._ackTimeout:
                if not isResend:
                    self._deliveryTimedOut(otherID, msgID, msgHTML, msgTime)
                removedIDs.append(msgID)
        
        if len(removedIDs) > 0:
            for msgID in removedIDs:
                self._waitingForAck.pop(msgID)
    
    def _deliveryTimedOut(self, otherID, msgID, msgHTML, msgTime):
        self._hasUndelivered = True
        self._addOwnMessage(otherID, msgID, msgHTML, msgTime, ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED, u"", -1)
        
    def _checkAndResendValidID(self, otherID, oldMsgID, answerDict, isNoResend=False, msgHTML=None, recvTime=None):
        if u"validID" in answerDict:
            # seems my next message ID is invalid
            newValue = max(self._nextMessageID, answerDict[u"validID"])
            if newValue != self._nextMessageID:
                self.logger.info("Adjusting incorrect next message ID. Was %d, set to %d", self._nextMessageID, newValue)
                self._nextMessageID = newValue
                
            if isNoResend:
                # just send message again, no need to update storage
                newID = self._getNextMessageID()
            else:
                # need to resend message
                msgTuple = self._getStorage().getMessage(otherID, oldMsgID, True)
                if msgTuple is None:
                    self.logger.error("Error trying to resend message %d with a new ID (message not found)", oldMsgID)
                    return False
                msgHTML = msgTuple[ChatMessagesStorage.MSG_TEXT_COL]
                recvTime = msgTuple[ChatMessagesStorage.MSG_TIME_COL]
                
                newID = self._getNextMessageID()
                if not self._getStorage().updateMessageID(otherID, oldMsgID, newID, True):
                    self.logger.error("Error trying to resend message %d with a new ID (could not update message ID)", oldMsgID)
                    return False
                self.messageIDChanged.emit(otherID, oldMsgID, newID)
                
            self.sendMessage(otherID,
                             msgHTML,
                             newID,
                             recvTime,
                             isNoResend)
            return True
        return False
        
    def _checkDelayedAck(self, otherID, msgID, error, answerDict, recvTime):
        currentState = self._getStorage().getMessageState(otherID, msgID)
        if currentState == ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED:
            if error and self._checkAndResendValidID(otherID, msgID, answerDict):
                # message needed to be resent with a different message ID, so we wait for another ACK
                return
            try:
                self._getStorage().updateMessageState(msgID, ChatMessagesModel.MESSAGE_STATE_ERROR if error else ChatMessagesModel.MESSAGE_STATE_OK)
                self._getStorage().updateReceiveTime(otherID, msgID, recvTime)
            except:
                self.logger.exception("Error updating message state")
            
            self.delayedDelivery.emit(otherID, msgID, recvTime, error, self._getAnswerErrorMessage(error, answerDict, msgID, otherID))
            return True
        return False
     
    def _getAnswerErrorMessage(self, error, answerDict, msgID, otherID):
        errorMsg = u""
        if error:
            if u"err" in answerDict:
                errorMsg = answerDict[u"err"]
                self.logger.warning("Message %s could not be processed by peer '%s': %s", msgID, otherID, errorMsg)
            else:
                self.logger.warning("Message %s could not be processed by peer '%s'", msgID, otherID)
        return errorMsg
     
    def processAck(self, ackPeerID, valueJSON, error=False):
        self._processAck.emit(ackPeerID, valueJSON, error)
    @loggingSlot(object, object, bool)
    def _processAckSlot(self, ackPeerID, valueJSON, error):
        ackPeerID = convert_string(ackPeerID)
        valueJSON = convert_string(valueJSON)
        
        try:
            answerDict = json.loads(valueJSON)
        except:
            self.logger.error("Error reading ACK message: %s", valueJSON)
            return
        
        if not u"id" in answerDict:
            self.logger.error("No message ID in ACK message: %s", valueJSON)
            return
        
        if u"recvTime" in answerDict:
            recvTime = answerDict[u"recvTime"]
        else:
            recvTime = time()
            
        msgID = answerDict[u"id"]
        
        if not msgID in self._waitingForAck:
            if self._checkDelayedAck(ackPeerID, msgID, error, answerDict, recvTime):
                self.logger.debug("Delayed delivery of message %d to %s", msgID, ackPeerID)
                return
            self.logger.debug("Received ACK for message ID '%s' that I was not waiting for.", msgID)
            return
        
        otherID, msgTime, msgHTML, isResend = self._waitingForAck.pop(msgID)
        if otherID != ackPeerID:
            self.logger.warning("Received ACK from different peer ID than the message was sent to ('%s' != '%s')", otherID, ackPeerID)
            return
        
        if isResend:
            self._checkDelayedAck(otherID, msgID, error, answerDict, recvTime)
        else:
            if error and self._checkAndResendValidID(otherID, msgID, answerDict, isNoResend=True, msgHTML=msgHTML, recvTime=recvTime):
                return
            errorMsg = self._getAnswerErrorMessage(error, answerDict, msgID, otherID)
            self._addOwnMessage(otherID,
                                msgID,
                                msgHTML,
                                msgTime,
                                ChatMessagesModel.MESSAGE_STATE_ERROR if error else ChatMessagesModel.MESSAGE_STATE_OK,
                                errorMsg,
                                recvTime)
        
    def _addOwnMessage(self, otherID, msgID, msgHTML, msgTime, status, errorMsg, recvTime):
        self.displayOwnMessage.emit(otherID, msgID, recvTime, msgHTML, msgTime, status, errorMsg)
        try:
            self._getStorage().addOwnMessage(msgID, otherID, msgTime, status, msgHTML, recvTime)
        except:
            self.logger.exception("Error storing own message")
        
    def processMessage(self, otherID, msgDictJSON):
        self._processMessage.emit(otherID, msgDictJSON)
    @loggingSlot(object, object)
    def _processMessageSlot(self, otherID, msgDictJSON):
        otherID = convert_string(otherID)
        msgDictJSON = convert_string(msgDictJSON)
        
        try:
            msgDict = json.loads(msgDictJSON)
        except:
            self._sendAnswer(otherID, {}, "Error loading message: %s" % msgDictJSON)
            return
        
        if u"id" not in msgDict or msgDict[u"id"] == None:
            # cannot send answer actually, but handle error
            self._sendAnswer(otherID, msgDict, u"Message has no ID: %s" % msgDict)
            return
        
        if not u"data" in msgDict:
            self._sendAnswer(otherID, msgDict, u"Message does not contain data: %s" % msgDict)
            return
        
        if u"format" in msgDict:
            if msgDict[u"format"] == u"html":
                msgHTML = msgDict[u"data"]
            else:
                self._sendAnswer(otherID, msgDict, u"Unknown message format: %s" % msgDict[u"format"])
                return
        else:
            self.logger.info("Message without format. Assuming plain text or HTML.")
            msgHTML = msgDict[u"data"]

        if u"time" in msgDict:
            msgTime = msgDict[u"time"]
            messageTimeUnknown = False
        else:
            msgTime = time()
            messageTimeUnknown = True
        
        # check if we already know the message (our ACK might not have been delivered)
        try:
            containsMessage = self._getStorage().containsMessage(otherID,
                                                                 msgDict[u"id"],
                                                                 msgHTML,
                                                                 None if messageTimeUnknown else msgTime,
                                                                 ownMessage=False)
            if not containsMessage:
                self.newMessage.emit(otherID, msgHTML, msgTime, msgDict)
            else:
                self.logger.debug("Received message from %s that I already know (id %d)", otherID, msgDict[u"id"])
                # send ACK again
                self._sendAnswer(otherID, msgDict)
        except InconsistentIDError as e:
            self._sendInvalidID(otherID, msgDict, validID=e.validID)
        
    def receivedSuccessfully(self, otherID, msgHTML, msgTime, msgDict, recvTime):
        self._receivedSuccessfully.emit(otherID, msgHTML, msgTime, msgDict, recvTime)
    @loggingSlot(object, object, float, object, float)
    def _receivedSuccessfullySlot(self, otherID, msgHTML, msgTime, msgDict, recvTime):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        
        containsMessage = self._getStorage().containsMessage(otherID,
                                                             msgDict[u"id"],
                                                             msgHTML,
                                                             msgTime,
                                                             ownMessage=False)
        if containsMessage:
            self.logger.debug("Received same message again from %s within a very short time interval", otherID)
            return
            
        try:
            self._getStorage().addOtherMessage(msgDict[u"id"], otherID, msgTime, msgHTML, recvTime)
        except:
            self.logger.exception("Error storing partner message")
        self._sendAnswer(otherID, msgDict, recvTime=recvTime)
        
    def errorReceivingMessage(self, otherID, msgDict, errorMsg):
        self._errorReceivingMessage.emit(otherID, msgDict, errorMsg)
    @loggingSlot(object, object, object)
    def _errorReceivingMessageSlot(self, otherID, msgDict, errorMsg):
        otherID = convert_string(otherID)
        errorMsg = convert_string(errorMsg)
        self._sendAnswer(otherID, msgDict, errorMsg)
        
    def _sendInvalidID(self, otherID, msgDict, validID):
        self._sendAnswer(otherID, msgDict, validID=validID)
        
    def _sendAnswer(self, otherID, msgDict, errorMsg=None, recvTime=None, validID=None):
        if u"id" not in msgDict:
            if errorMsg:
                self.logger.error(errorMsg)
            self.logger.debug("Message has no ID, cannot send answer.")
            return
        
        msgID = msgDict[u"id"]
        answerDict = {u"id": msgID}
        if not errorMsg and not validID:
            if recvTime == None:
                # sending ACK again - get receive time from db
                recvTime = self._delegate.getStorage().getReceiveTime(otherID, msgID)
            if recvTime == None:
                # should not happen
                self.logger.error("Could not determine receive time for msg %s from %s", msgID, otherID)
                recvTime = time()
            
            answerDict[u"recvTime"] = recvTime
            get_server().call("HELO_PM_ACK " + json.dumps(answerDict), peerIDs=[otherID])
        elif validID:
            # partner sent message with invalid ID
            answerDict[u"err"] = u"Inconsistent ID"
            answerDict[u"validID"] = validID 
            self.logger.warning(u"Received message with inconsistent ID from %s, ID was %d, next valid ID is %d", otherID, msgDict[u"id"], validID)
            get_server().call("HELO_PM_ERROR " + json.dumps(answerDict), peerIDs=[otherID])
        else:
            # default error handling, send error message
            answerDict[u"err"] = errorMsg 
            self.logger.error(errorMsg)
            get_server().call("HELO_PM_ERROR " + json.dumps(answerDict), peerIDs=[otherID])  
    
    ############### PUBLIC SLOTS #################
    
    @loggingSlot(object, object)
    def sendMessage(self, otherID, msgHTML, msgID=None, msgTime=None, isNoResend=False):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        
        if msgID == None:
            msgID = self._getNextMessageID()
            isResend = False
        else:
            isResend = True
            
        if isNoResend:
            isResend = False
        
        if msgTime == None:
            msgTime = time()
        
        msgDict = {u"id": msgID,
                   u"format": u"html",
                   u"data": msgHTML,
                   u"time": msgTime}
        
        try:
            msgDictJSON = json.dumps(msgDict)
        except:
            self.logger.exception("Error serializing private message: %s", msgDict)
            return
        
        get_server().call("HELO_PM " + msgDictJSON, peerIDs=[otherID])
        self._waitingForAck[msgID] = (otherID,
                                      time() if isResend else msgTime,
                                      msgHTML,
                                      isResend)

    @loggingSlot(object)
    def sendTyping(self, otherID):
        otherID = convert_string(otherID)
        get_server().call("HELO_PM_TYPING 0", peerIDs=[otherID])
        
    @loggingSlot(object)
    def sendCleared(self, otherID):
        otherID = convert_string(otherID)
        get_server().call("HELO_PM_CLEARED 0", peerIDs=[otherID])
