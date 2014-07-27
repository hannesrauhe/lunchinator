from PyQt4.QtGui import QWidget, QVBoxLayout, QSizePolicy,\
    QFrame, QIcon, QHBoxLayout,\
    QLabel, QPixmap, QTextCharFormat, QTextCursor, QToolButton, QMenu
from PyQt4.QtCore import Qt, QSize, pyqtSignal, QRegExp, QTimer

from lunchinator import convert_string, get_settings, get_notification_center,\
    get_peers
from lunchinator.history_line_edit import HistoryTextEdit
from lunchinator.peer_actions.peer_action_utils import showPeerActionsPopup,\
    initializePeerActionsMenu
from private_messages.chat_messages_view import ChatMessagesView
from private_messages.chat_messages_model import ChatMessagesModel

from xml.etree import ElementTree
from StringIO import StringIO
from functools import partial
from time import time

class ChatWidget(QWidget):
    PREFERRED_WIDTH = 400
    _URI_REGEX="""
    (
      (
        [A-Za-z][A-Za-z0-9\+\.\-]*:\/\/
        [A-Za-z0-9\.\-]+
        |
        www\.
        [A-Za-z0-9\.\-]+
        \.[A-Za-z]+
      )
      (
        (?:\/[\+~%\/\.\w\-]*)
        ?\??(?:[\-\+=&;%@\.\w]*) 
        #?(?:[\.\!\/\\\w]*)
      )?
    )
    """.replace("\n", "").replace(" ", "")
    
    _MAIL_REGEX="""
    (
      (
        [\-;:&=\+\$,\w]+@
        [A-Za-z0-9\.\-]+
        \.[A-Za-z]+
      )
    )
    """.replace("\n", "").replace(" ", "")
    
    _URI_MATCHER=QRegExp(_URI_REGEX)
    _MAIL_MATCHER=QRegExp(_MAIL_REGEX)
    _TIME_ROW_INTERVAL = 10*60 # once every 10 minutes
    
    sendMessage = pyqtSignal(unicode, unicode) # peer ID, message HTML
    typing = pyqtSignal()
    cleared = pyqtSignal()
        
    def __init__(self, parent, ownName, otherName, ownPicFile, otherPicFile, otherID):
        super(ChatWidget, self).__init__(parent)
        
        self._offline = False
        self._delivering = False
        self._lastTimeRow = 0
        self._textChanged = False
        self._keepEntryText = False
        
        self._typingTimer = QTimer(self)
        self._typingTimer.timeout.connect(self._checkTyping)
        self._typingTimer.start(1000)
        self._entryWasEmpty = True
        self._selfWasTyping = False
        self._otherWasTyping = False
        self._lastTimeSelfTyped = None
        self._lastTimePartnerTyped = None
        
        self._otherID = otherID
        
        self._otherName = otherName
        self._ownName = ownName
        
        try:
            from PyQt4.QtGui import QCommonStyle, QStyle
            style = QCommonStyle()
            self._errIcon = style.standardIcon(QStyle.SP_MessageBoxCritical)
            self._warnIcon = style.standardIcon(QStyle.SP_MessageBoxWarning)
        except:
            self._errIcon = QIcon(get_settings().get_resource("images", "error.png"))
            self._warnIcon = QIcon(get_settings().get_resource("images", "warning.png"))
        
        self._initMessageModel()
        self._initMessageTable()
        self._initTextEntry()
        self._initStatusLabel()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(0)
        
        self._addTopLayout(mainLayout)
        mainLayout.addWidget(self.table)
        mainLayout.addWidget(self._statusLabel)
        mainLayout.addWidget(self.entry)
        
        # initialize GUI
        self._updateOtherName()
        self._updateOwnName()
        self.setOwnIconPath(ownPicFile)
        self.setOtherIconPath(otherPicFile)
                
        # TODO option to change behavior
        self.entry.returnPressed.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
        get_notification_center().connectPeerAppended(self._peerUpdated)
        get_notification_center().connectPeerUpdated(self._peerUpdated)
        get_notification_center().connectPeerRemoved(self._peerRemoved)
        get_notification_center().connectAvatarChanged(self._avatarChanged)
        get_notification_center().connectDisplayedPeerNameChanged(self._displayedPeerNameChanged)
        
        if get_peers() != None:
            self._setOffline(not get_peers().isPeerID(pID=self._otherID))
        else:
            self._setOffline(True)
        
    def _setOffline(self, offline):
        if self._offline == offline:
            return
        
        self._offline = offline
        self._updateOtherName()
        
    def _updateOtherName(self):
        if self._offline:
            title = self._otherName + " (Offline)"
        else:
            title = self._otherName
            
        self._otherPicLabel.setEnabled(not self._offline)
        self._otherNameLabel.setText(title)
        self.parent().setWindowTitle(title)
        self._checkEntryState()
        
    def _updateOwnName(self):
        self._ownNameLabel.setText(self._ownName)
        
    def _peerUpdated(self, peerID, peerInfo):
        peerID = convert_string(peerID)
        if peerID == self._otherID:
            self._setOffline(u"PM_v" not in peerInfo)
    
    def _peerRemoved(self, peerID):
        peerID = convert_string(peerID)
        if peerID == self._otherID:
            self._setOffline(True)
            
    def _avatarChanged(self, peerID, newFile):
        peerID = convert_string(peerID)
        newFile = convert_string(newFile)
        
        if peerID == self._otherID:
            self.setOtherIconPath(get_peers().getPeerAvatarFile(pID=peerID))
        elif peerID == get_settings().get_ID():
            self.setOwnIconPath(get_peers().getPeerAvatarFile(pID=peerID))
            
    def _displayedPeerNameChanged(self, pID, newName, _infoDict):
        pID = convert_string(pID)
        newName = convert_string(newName)
        
        if pID == self._otherID:
            self._otherName = newName
            self._updateOtherName()
        if pID == get_settings().get_ID():
            self._ownName = newName
            self._updateOwnName()
        
    def _clearEntry(self):
        self.entry.clear()
        self.entry.setCurrentCharFormat(QTextCharFormat())
        
    def _checkEntryState(self):
        self.entry.setEnabled(not self._offline and not self._delivering)
        if self._offline:
            if self.entry.document().isEmpty():
                self._clearEntry()
                self.entry.setText(u"Partner is offline")
            else:
                self._keepEntryText = True
        elif self._delivering:
            self._clearEntry()
            self.entry.setText(u"Delivering...")
        elif not self._keepEntryText:
            self._clearEntry()
            
        if self._keepEntryText and not self._offline:
            # reset if not offline any more
            self._keepEntryText = False
        
    def nextInFocusChain(self):
        return self.entry
    
    def previousInFocusChain(self):
        return self.entry
    
    def focusInEvent(self, _event):
        self.entry.setFocus(Qt.OtherFocusReason)
        
    def _filterPeerAction(self, pluginName, action):
        return pluginName != u"hannesrauhe.lunchinator.private_messages" or action.getName() != "Open Chat"
        
    def _addTopLayout(self, mainLayout):
        topWidget = QWidget(self)
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        self._otherNameLabel = QToolButton(topWidget)
        self._otherNameLabel.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._otherNameLabel.setStyleSheet("QToolButton { text-align: left; font-size: 13pt; border: none; margin-left: -5px; padding-right:5px; padding-bottom: -2px;}")
        self._otherNameLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        self._otherNameLabel.customContextMenuRequested.connect(partial(showPeerActionsPopup, self._otherID, self._filterPeerAction, self._otherNameLabel))
        self._otherNameLabel.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self._otherNameLabel)
        menu.aboutToShow.connect(partial(initializePeerActionsMenu, menu, self._otherID, self._filterPeerAction))
        self._otherNameLabel.setMenu(menu)
        
        self._otherPicLabel = QLabel(topWidget)
        topLayout.addWidget(self._otherPicLabel, 0, Qt.AlignLeft)
        topLayout.addWidget(self._otherNameLabel, 1, Qt.AlignLeft)
        
        self._ownNameLabel = QToolButton(topWidget)
        self._ownNameLabel.setStyleSheet("QToolButton { text-align: left; font-size: 13pt; border: none; margin-right: -5px;}")
        self._ownNameLabel.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._ownPicLabel = QLabel(topWidget)
        topLayout.addWidget(self._ownNameLabel, 1, Qt.AlignRight)
        topLayout.addWidget(self._ownPicLabel, 0, Qt.AlignRight)
        
        mainLayout.addWidget(topWidget)
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        mainLayout.addSpacing(5)
        mainLayout.addWidget(separator)
        mainLayout.addSpacing(5)
        
    def _initTextEntry(self):
        self.entry = HistoryTextEdit(self, True)
        self.entry.textChanged.connect(self._textChangedSlot)
        
    def _initStatusLabel(self):
        self._statusLabel = QLabel(self)
        self._statusLabel.setContentsMargins(0, 5, 0, 5)
        self._statusLabel.setVisible(False)
        
    def _initMessageModel(self):
        self._model = ChatMessagesModel(self, self)
        
    def _initMessageTable(self):
        self.table = ChatMessagesView(self._model, self)
        
    def _textChangedSlot(self):
        if not self.entry.isEnabled() or self.entry.document().isEmpty():
            self._textChanged = False
            if not self._entryWasEmpty:
                self._entryWasEmpty = True
                self._selfWasTyping = False
                self._informCleared()
        elif not self._selfWasTyping:
            self._entryWasEmpty = False
            self._informTyping()
            self._selfWasTyping = True
            self._lastTimeSelfTyped = time()
        else:
            self._textChanged = True
            
    def _checkTyping(self):
        curTime = time()
        if self._textChanged:
            self._informTyping()
            # TODO do we really need thread safety here?
            self._textChanged = False
            self._lastTimeSelfTyped = curTime
        elif self._selfWasTyping and curTime - self._lastTimeSelfTyped > 3:
            self._selfWasTyping = False    
            
        if self._otherWasTyping and curTime - self._lastTimePartnerTyped > 3:
            self.setStatus(self.getOtherName() + " paused typing.")
            self._otherWasTyping = False
            
    def _informTyping(self):
        if not self._offline:
            self.typing.emit()
        
    def _informCleared(self):
        if not self._offline:
            self.cleared.emit()
            
    def otherIsTyping(self):
        if not self._otherWasTyping:
            self._otherWasTyping = True
            self.setStatus(self.getOtherName() + " is typing a message...")
        self._lastTimePartnerTyped = time()
        
    def otherCleared(self):
        self._otherWasTyping = False
        self.setStatus(None)
       
    def scrollToEnd(self, force=True):
        lastIndex = self._model.getLastIndex()
        if not force:
            rect = self.table.visualRect(lastIndex)
            if rect.topLeft().y() > self.table.viewport().height():
                # last item not visible -> don't scroll
                return
        self.table.scrollTo(lastIndex)
        
    def addTimeRow(self, rtime, scroll=True):
        self._model.addTimeRow(rtime)
        if scroll:
            self.scrollToEnd(force=False)
        
    def _checkTime(self, msgTime, scroll):
        if msgTime - self._lastTimeRow > self._TIME_ROW_INTERVAL:
            self.addTimeRow(msgTime, scroll)
            self._lastTimeRow = msgTime
        
    def addOwnMessage(self, msgID, recvTime, msg, msgTime, messageState=None, toolTip=None, scroll=True):
        self._checkTime(msgTime, scroll)
        self._model.addOwnMessage(msgID, recvTime, msg, msgTime, messageState, toolTip)
        self.entry.clear()
        self._delivering = False
        self._checkEntryState()
        self.entry.setFocus(Qt.OtherFocusReason)
        if scroll:
            self.scrollToEnd()
        
    def addOtherMessage(self, msg, msgTime, recvTime, scroll=True):
        self._checkTime(msgTime, scroll)
        self._model.addOtherMessage(msg, msgTime, recvTime)
        if scroll:
            self.scrollToEnd(force=False)
        
    def delayedDelivery(self, msgID, recvTime, error, errorMessage):
        return self._model.messageDelivered(msgID, recvTime, error, errorMessage)
        
    def messageIDChanged(self, oldID, newID):
        self._model.messageIDChanged(oldID, newID)
        
    def canClose(self):
        return not self._delivering
    
    def finish(self):
        get_notification_center().disconnectPeerAppended(self._peerUpdated)
        get_notification_center().disconnectPeerUpdated(self._peerUpdated)
        get_notification_center().disconnectPeerRemoved(self._peerRemoved)
        get_notification_center().disconnectAvatarChanged(self._avatarChanged)
        get_notification_center().disconnectDisplayedPeerNameChanged(self._displayedPeerNameChanged)
        
        if self._typingTimer is not None:
            self._typingTimer.stop()
            self._typingTimer.deleteLater()
            self._typingTimer = None
        
    def getOwnIcon(self):
        return self._ownIcon    
    
    def getOwnIconPath(self):
        return self._ownIconPath
    def setOwnIconPath(self, iconPath):
        if not iconPath:
            iconPath = get_settings().get_resource("images", "me.png")
        self._ownIconPath = iconPath
        self._ownIcon = QIcon(iconPath)
        self._ownPicLabel.setPixmap(QPixmap(self._ownIconPath).scaled(24,24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._model.setOwnIcon(self._ownIcon)

    def getOtherIcon(self):
        return self._otherIcon        
    
    def getOtherIconPath(self):
        return self._otherIconPath
    def setOtherIconPath(self, iconPath):
        if not iconPath:
            iconPath = get_settings().get_resource("images", "lunchinator.png")
        self._otherIconPath = iconPath
        self._otherIcon = QIcon(iconPath)
        self._otherPicLabel.setPixmap(QPixmap(self._otherIconPath).scaled(24,24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._model.setOtherIcon(self._otherIcon)
        
    def getOtherName(self):
        return self._otherName
        
    def getWarnIcon(self):
        return self._warnIcon
    
    def getErrorIcon(self):
        return self._errIcon
    
    def setStatus(self, statusText):
        if statusText:
            self._statusLabel.setText(statusText)
            self._statusLabel.setVisible(True)
        else:
            self._statusLabel.setVisible(False)
        
    def eventTriggered(self):
        self._detectHyperlinks()
        text = self._cleanHTML(convert_string(self.entry.toHtml()))
        self.sendMessage.emit(self._otherID, text)
        self._delivering = True
        self._checkEntryState()

    def _cleanHTML(self, html):
        # only body, no paragraph attributes
        html = html.encode("utf-8")
        cleaned = u""
        e = ElementTree.fromstring(html)
        body = e.iter("html").next().iter("body").next()
        for p in body.iter("p"):
            p.attrib = {}
            sio = StringIO()
            ElementTree.ElementTree(p).write(sio, "utf-8")
            cleaned += sio.getvalue().replace('<br />', '').decode("utf-8")
        return cleaned

    def _insertAnchors(self, cursor, plainText, matcher, hrefFunc):
        pos = 0
        while pos != -1:
            pos = matcher.indexIn(plainText, pos)
            if pos == -1:
                break
            
            cursor.setPosition(pos);
            cursor.setPosition(pos + matcher.matchedLength(), QTextCursor.KeepAnchor)

            fmt = QTextCharFormat()
            fmt.setAnchor(True)
            fmt.setAnchorHref(hrefFunc(matcher.cap()))
            cursor.mergeCharFormat(fmt)
            
            pos += matcher.matchedLength()
        
    def _detectHyperlinks(self):
        cursor = QTextCursor(self.entry.document())
        plainText = self.entry.toPlainText()
        self._insertAnchors(cursor, plainText, self._URI_MATCHER, lambda uri : u"http://" + convert_string(uri) if uri.startsWith(u"www.") else uri)
        self._insertAnchors(cursor, plainText, self._MAIL_MATCHER, lambda mail : u"mailto:" + convert_string(mail))
        
    def sizeHint(self):
        sizeHint = QWidget.sizeHint(self)
        return QSize(self.PREFERRED_WIDTH, sizeHint.height())
        
if __name__ == '__main__':
    from time import time
    from lunchinator.plugin import iface_gui_plugin
    
    def createTable(window):
        ownIcon = get_settings().get_resource("images", "me.png")
        otherIcon = get_settings().get_resource("images", "lunchinator.png")
        tw = ChatWidget(window, "Me", "Other Guy", ownIcon, otherIcon, "ID")
        tw.addOwnMessage(0, time(),
                         "foo<br> <a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a> Nachrichten",
                         time(),
                         ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED)
        tw.addOtherMessage("<a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a>",
                           time(), time())
        tw.addOtherMessage("foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                           time(), time())
        tw.addTimeRow(time())
        tw.addOtherMessage("foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                           time(), time())
        tw.addOtherMessage("foo",
                           time(), time())
        tw.addOtherMessage("foo",
                           time(), time())
        tw.addTimeRow(time())
        tw.addOtherMessage("<a href=\"mailto:info@lunchinator.de\">Lunchinator Mail</a>",
                           time(), time())
        tw.addOwnMessage(1, time(),
                         "bar",
                         time(),
                         ChatMessagesModel.MESSAGE_STATE_ERROR)
        tw.addOwnMessage(2, time(),
                         "foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                         time())
        tw.addOtherMessage("foo",
                           time(), time())
        tw.addOtherMessage("foo",
                           time(), time())
        tw.addOwnMessage(3, time(),
                         "bar",
                         time())
        tw.addTimeRow(time())
        
        tw._setOffline(False)
        
        tw.typing.connect(tw.otherIsTyping)
        tw.cleared.connect(tw.otherCleared)
        tw.sendMessage.connect(lambda pID, html : tw.addOwnMessage(0, time(), html, time()), type=Qt.QueuedConnection)
        
        return tw
        
    iface_gui_plugin.run_standalone(createTable)
    
