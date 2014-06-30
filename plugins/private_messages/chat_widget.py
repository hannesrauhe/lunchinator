from PyQt4.QtGui import QWidget, QVBoxLayout, QSizePolicy,\
    QFrame, QIcon, QHBoxLayout,\
    QLabel, QPixmap, QTextCharFormat, QTextCursor
from PyQt4.QtCore import Qt, QSize, pyqtSignal, QRegExp

from lunchinator import convert_string, get_settings, get_notification_center,\
    get_peers
from lunchinator.history_line_edit import HistoryTextEdit
from private_messages.chat_messages_view import ChatMessagesView
from private_messages.chat_messages_model import ChatMessagesModel

from xml.etree import ElementTree
from StringIO import StringIO
import os

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
        
    def __init__(self, parent, ownName, otherName, ownPicFile, otherPicFile, otherID):
        super(ChatWidget, self).__init__(parent)
        
        self._offline = False
        self._delivering = False
        self._lastTimeRow = 0
        
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
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(0)
        
        self._addTopLayout(mainLayout)
        mainLayout.addWidget(self.table)
        mainLayout.addWidget(self.entry)
        
        # initialize GUI
        self._updateOtherName()
        self._updateOwnName()
        self.setOwnIconPath(ownPicFile)
        self.setOtherIconPath(otherPicFile)
                
        # TODO option to change behavior
        self.entry.returnPressed.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
        get_notification_center().connectPeerAppended(self._peerAppended)
        get_notification_center().connectAvatarChanged(self._avatarChanged)
        get_notification_center().connectPeerRemoved(self._peerRemoved)
        get_notification_center().connectDisplayedPeerNameChanged(self._displayedPeerNameChanged)
        
        if get_peers():
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
        
    def _peerAppended(self, peerID, peerInfo):
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
            self.setOtherIconPath(os.path.join(get_settings().get_avatar_dir(), newFile))
        elif peerID == get_settings().get_ID():
            self.setOwnIconPath(os.path.join(get_settings().get_avatar_dir(), newFile))
            
    def _displayedPeerNameChanged(self, pID, newName, _infoDict):
        pID = convert_string(pID)
        newName = convert_string(newName)
        
        if pID == self._otherID:
            self._otherName = newName
            self._updateOtherName()
        elif pID == get_settings().get_ID():
            self._ownName = newName
            self._updateOwnName()
        
    def _checkEntryState(self):
        self.entry.setEnabled(not self._offline and not self._delivering)
        if self._offline:
            self.entry.setText(u"Partner is offline")
        elif self._delivering:
            self.entry.setText(u"Delivering...")
        else:
            self.entry.setText(u"")
        
    def nextInFocusChain(self):
        return self.entry
    
    def previousInFocusChain(self):
        return self.entry
    
    def focusInEvent(self, _event):
        self.entry.setFocus(Qt.OtherFocusReason)
        
    def _addTopLayout(self, mainLayout):
        topWidget = QWidget(self)
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        self._otherNameLabel = QLabel(topWidget)
        self._otherPicLabel = QLabel(topWidget)
        topLayout.addWidget(self._otherPicLabel, 0, Qt.AlignLeft)
        topLayout.addWidget(self._otherNameLabel, 1, Qt.AlignLeft)
        
        self._ownNameLabel = QLabel(topWidget)
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
        
    def _initMessageModel(self):
        self._model = ChatMessagesModel(self, self)
        
    def _initMessageTable(self):
        self.table = ChatMessagesView(self._model, self)
       
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
        
    def addOwnMessage(self, msgID, msg, msgTime, messageState=None, toolTip=None, scroll=True):
        self._checkTime(msgTime, scroll)
        self._model.addOwnMessage(msgID, msg, msgTime, messageState, toolTip)
        self.entry.clear()
        self._delivering = False
        self._checkEntryState()
        self.entry.setFocus(Qt.OtherFocusReason)
        if scroll:
            self.scrollToEnd()
        
    def addOtherMessage(self, msg, msgTime, scroll=True):
        self._checkTime(msgTime, scroll)
        self._model.addOtherMessage(msg, msgTime)
        if scroll:
            self.scrollToEnd(force=False)
        
    def delayedDelivery(self, msgID, error, errorMessage):
        return self._model.messageDelivered(msgID, error, errorMessage)
        
    def canClose(self):
        return not self._delivering
        
    def getOwnIcon(self):
        return self._ownIcon    
    
    def getOwnIconPath(self):
        return self._ownIconPath
    def setOwnIconPath(self, iconPath):
        self._ownIconPath = iconPath
        self._ownIcon = QIcon(iconPath)
        self._ownPicLabel.setPixmap(QPixmap(self._ownIconPath).scaled(24,24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._model.setOwnIcon(self._ownIcon)

    def getOtherIcon(self):
        return self._otherIcon        
    
    def getOtherIconPath(self):
        return self._otherIconPath
    def setOtherIconPath(self, iconPath):
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
    from lunchinator.iface_plugins import iface_gui_plugin
    
    def createTable(window):
        ownIcon = get_settings().get_resource("images", "me.png")
        otherIcon = get_settings().get_resource("images", "lunchinator.png")
        tw = ChatWidget(window, "Me", "Other Guy", ownIcon, otherIcon, "ID")
        tw.addOwnMessage(0,
                         "foo<br> <a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a> Nachrichten",
                         time(),
                         ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED)
        tw.addOtherMessage("<a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a>",
                           time())
        tw.addOtherMessage("foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                           time())
        tw.addTimeRow(time())
        tw.addOtherMessage("foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                           time())
        tw.addOtherMessage("foo",
                           time())
        tw.addOtherMessage("foo",
                           time())
        tw.addTimeRow(time())
        tw.addOtherMessage("<a href=\"mailto:info@lunchinator.de\">Lunchinator Mail</a>",
                           time())
        tw.addOwnMessage(1,
                         "bar",
                         time(),
                         ChatMessagesModel.MESSAGE_STATE_ERROR)
        tw.addOwnMessage(2,
                         "foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh",
                         time())
        tw.addOtherMessage("foo",
                           time())
        tw.addOtherMessage("foo",
                           time())
        tw.addOwnMessage(3,
                         "bar",
                         time())
        tw.addTimeRow(time())
        
        return tw
        
    iface_gui_plugin.run_standalone(createTable)
    
