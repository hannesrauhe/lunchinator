from private_messages.chat_messages_model import ChatMessagesModel

from lunchinator import log_exception, log_error, log_debug,\
    log_warning, log_info, convert_string, get_server, get_peers,\
    get_notification_center

from PyQt4.QtCore import pyqtSignal, pyqtSlot, QTimer, QObject
from time import time
import json
        
class ChatMessagesHandler(QObject):
    _STOP_RESEND_TIME = 60 # seconds until resending is stopped
    
    # other ID, message ID, receive time, HTML, time, state, error message
    displayOwnMessage = pyqtSignal(unicode, int, float, unicode, float, int, unicode)
    # other ID, message ID, receive time, error, error message
    delayedDelivery = pyqtSignal(unicode, int, float, bool, unicode)
    # otherID, msgHTML, msgTime
    newMessage = pyqtSignal(unicode, unicode, float, dict)
    
    # private signals
    _processAck = pyqtSignal(unicode, unicode, bool)
    _processMessage = pyqtSignal(unicode, unicode)
    _receivedSuccessfully = pyqtSignal(unicode, unicode, float, dict, float)
    _errorReceivingMessage = pyqtSignal(unicode, dict, unicode)
    
    def __init__(self, delegate, ackTimeout):
        super(ChatMessagesHandler, self).__init__()
        
        self._delegate = delegate
        self._ackTimeout = ackTimeout
        self._waitingForAck = {} # message ID : (otherID, time, message, isResend)
        self._nextMessageID = None
        
        self._cleanupTimer = QTimer(self)
        self._cleanupTimer.timeout.connect(self.cleanup)
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
        if self._nextMessageID == None:
            self._nextMessageID = self._getStorage().getNextMessageID()
        
        try:
            return self._nextMessageID
        finally:
            self._nextMessageID += 1
        
    @pyqtSlot(unicode, dict)
    def _peerAppended(self, peerID, _infoDict):
        peerID = convert_string(peerID)
        self._resendUndeliveredMessages(curTime=None, partner=peerID, force=True)
        
    def _resendUndeliveredMessages(self, curTime, partner=None, force=False):    
        for msgTuple in self._getStorage().getRecentUndeliveredMessages(partner):
            msgTime = msgTuple[3]
            if not force:
                timeout = int(curTime - msgTime)
                if timeout > self._STOP_RESEND_TIME:
                    continue
                
            msgID = msgTuple[1]
            if msgID in self._waitingForAck:
                # already resent and waiting for ACK
                continue
            
            # check if partner is online
            otherID = msgTuple[0]
            if get_peers().isPeerID(pID=otherID):
                log_debug("Resending undelivered message %d to peer '%s'" % (msgID, otherID))
                # partner is online, resend message
                msgHTML = msgTuple[5]
                self.sendMessage(otherID, msgHTML, msgID, msgTime)
    
    @pyqtSlot()
    def cleanup(self):
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
        self._addOwnMessage(otherID, msgID, msgHTML, msgTime, ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED, u"", -1)
        
    def _checkDelayedAck(self, otherID, msgID, error, answerDict, recvTime):
        currentState = self._getStorage().getMessageState(otherID, msgID)
        if currentState == ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED:
            try:
                self._getStorage().updateMessageState(msgID, ChatMessagesModel.MESSAGE_STATE_ERROR if error else ChatMessagesModel.MESSAGE_STATE_OK)
                self._getStorage().updateReceiveTime(otherID, msgID, recvTime)
            except:
                log_exception("Error updating message state")
            
            self.delayedDelivery.emit(otherID, msgID, recvTime, error, self._getAnswerErrorMessage(error, answerDict, msgID, otherID))
            return True
        return False
     
    def _getAnswerErrorMessage(self, error, answerDict, msgID, otherID):
        errorMsg = u""
        if error:
            if u"err" in answerDict:
                errorMsg = answerDict[u"err"]
                log_warning("Message %s could not be processed by peer '%s': %s" % (msgID, otherID, errorMsg))
            else:
                log_warning("Message %s could not be processed by peer '%s'" % (msgID, otherID))
        return errorMsg
     
    def processAck(self, ackPeerID, valueJSON, error=False):
        self._processAck.emit(ackPeerID, valueJSON, error)
    @pyqtSlot(unicode, unicode, bool)
    def _processAckSlot(self, ackPeerID, valueJSON, error):
        ackPeerID = convert_string(ackPeerID)
        valueJSON = convert_string(valueJSON)
        
        try:
            answerDict = json.loads(valueJSON)
        except:
            log_error("Error reading ACK message:", valueJSON)
            return
        
        if not u"id" in answerDict:
            log_error("No message ID in ACK message:", valueJSON)
            return
        
        if u"recvTime" in answerDict:
            recvTime = answerDict[u"recvTime"]
        else:
            recvTime = time()
            
        msgID = answerDict[u"id"]
        if not msgID in self._waitingForAck:
            if self._checkDelayedAck(ackPeerID, msgID, error, answerDict, recvTime):
                log_debug("Delayed delivery of message", msgID, "to", ackPeerID)
                return
            log_debug("Received ACK for message ID '%s' that I was not waiting for." % msgID)
            return
        
        otherID, msgTime, msgHTML, isResend = self._waitingForAck.pop(msgID)
        if otherID != ackPeerID:
            log_warning("Received ACK from different peer ID than the message was sent to ('%s' != '%s')" % (otherID, ackPeerID))
            return
        
        if isResend:
            self._checkDelayedAck(otherID, msgID, error, answerDict, recvTime)
        else:
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
            log_exception("Error storing own message")
        
    def processMessage(self, otherID, msgDictJSON):
        self._processMessage.emit(otherID, msgDictJSON)
    @pyqtSlot(unicode, unicode)
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
            log_info("Message without format. Assuming plain text or HTML.")
            msgHTML = msgDict[u"data"]

        if u"time" in msgDict:
            msgTime = msgDict[u"time"]
        else:
            msgTime = time()
        
        # check if we already know the message (our ACK might not have been delivered)
        if not self._getStorage().containsMessage(otherID, msgDict[u"id"], ownMessage=False):
            self.newMessage.emit(otherID, msgHTML, msgTime, msgDict)
        else:
            log_debug("Received message from %s that I already know (id %d)" % (otherID, msgDict[u"id"]))
            # send ACK again
            self._sendAnswer(otherID, msgDict)
        
    def receivedSuccessfully(self, otherID, msgHTML, msgTime, msgDict, recvTime):
        self._receivedSuccessfully.emit(otherID, msgHTML, msgTime, msgDict, recvTime)
    @pyqtSlot(unicode, unicode, float, dict, float)
    def _receivedSuccessfullySlot(self, otherID, msgHTML, msgTime, msgDict, recvTime):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        try:
            self._getStorage().addOtherMessage(msgDict[u"id"], otherID, msgTime, msgHTML, recvTime)
        except:
            log_exception("Error storing partner message")
        self._sendAnswer(otherID, msgDict, recvTime=recvTime)
        
    def errorReceivingMessage(self, otherID, msgDict, errorMsg):
        self._errorReceivingMessage.emit(otherID, msgDict, errorMsg)
    @pyqtSlot(unicode, dict, unicode)
    def _errorReceivingMessageSlot(self, otherID, msgDict, errorMsg):
        otherID = convert_string(otherID)
        errorMsg = convert_string(errorMsg)
        self._sendAnswer(otherID, msgDict, errorMsg)
        
    def _sendAnswer(self, otherID, msgDict, errorMsg=None, recvTime=None):
        if u"id" not in msgDict:
            if errorMsg:
                log_error(errorMsg)
            log_debug("Message has no ID, cannot send answer.")
            return
        
        msgID = msgDict[u"id"]
        answerDict = {u"id": msgID}
        if not errorMsg:
            if recvTime == None:
                # sending ACK again - get receive time from db
                recvTime = self._delegate.getStorage().getReceiveTime(otherID, msgID)
            if recvTime == None:
                # should not happen
                log_error("Could not determine receive time for msg", msgID, "from", otherID)
                recvTime = time()
            
            answerDict[u"recvTime"] = recvTime
            get_server().call("HELO_PM_ACK " + json.dumps(answerDict), peerIDs=[otherID])
        else:
            answerDict[u"err"] = errorMsg 
            log_error(errorMsg)
            get_server().call("HELO_PM_ERROR " + json.dumps(answerDict), peerIDs=[otherID])  
    
    @pyqtSlot(unicode, unicode)
    def sendMessage(self, otherID, msgHTML, msgID=None, msgTime=None):
        otherID = convert_string(otherID)
        msgHTML = convert_string(msgHTML)
        
        if msgID == None:
            msgID = self._getNextMessageID()
            isResend = False
        else:
            isResend = True
        
        if msgTime == None:
            msgTime = time()
        
        msgDict = {u"id": msgID,
                   u"format": u"html",
                   u"data": msgHTML,
                   u"time": msgTime}
        
        try:
            msgDictJSON = json.dumps(msgDict)
        except:
            log_exception("Error serializing private message:", msgDict)
            return
        
        get_server().call("HELO_PM " + msgDictJSON, peerIDs=[otherID])
        self._waitingForAck[msgID] = (otherID,
                                      time() if isResend else msgTime,
                                      msgHTML,
                                      isResend)

    def sendTyping(self, otherID):
        get_server().call("HELO_PM_TYPING 0", peerIDs=[otherID])
        
    def sendCleared(self, otherID):
        get_server().call("HELO_PM_CLEARED 0", peerIDs=[otherID])