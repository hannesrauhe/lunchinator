from PyQt4.QtGui import QWidget, QVBoxLayout, QSizePolicy,\
    QFrame, QIcon, QHBoxLayout,\
    QLabel, QPixmap, QTextCharFormat, QTextCursor
from PyQt4.QtCore import Qt, QSize, QVariant, pyqtSignal, QRegExp
from lunchinator import convert_string, get_settings
from lunchinator.history_line_edit import HistoryTextEdit
from private_messages.chat_messages_view import ChatMessagesView
from xml.etree import ElementTree
from private_messages.chat_messages_model import ChatMessagesModel
from cmath import rect
from StringIO import StringIO

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
    
    sendMessage = pyqtSignal(unicode, unicode) # peer ID, message HTML
        
    def __init__(self, parent, ownName, otherName, ownPicFile, otherPicFile, otherID):
        super(ChatWidget, self).__init__(parent)
        
        self._otherID = otherID
        
        self._otherName = otherName
        self._ownIcon = QIcon(ownPicFile)
        self._otherIcon = QIcon(otherPicFile)
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
        
        # TODO option to change behavior
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(0)
        
        self._addTopLayout(ownName, otherName, ownPicFile, otherPicFile, mainLayout)
        mainLayout.addWidget(self.table)
        mainLayout.addWidget(self.entry)
        
        self.entry.returnPressed.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def nextInFocusChain(self):
        return self.entry
    
    def previousInFocusChain(self):
        return self.entry
    
    def focusInEvent(self, _event):
        self.entry.setFocus(Qt.OtherFocusReason)
        
    def _addTopLayout(self, ownName, otherName, ownPicFile, otherPicFile, mainLayout):
        topWidget = QWidget(self)
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        otherNameLabel = QLabel(otherName, topWidget)
        otherPicLabel = QLabel(topWidget)
        otherPicLabel.setPixmap(QPixmap(otherPicFile).scaled(24,24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        topLayout.addWidget(otherPicLabel, 0, Qt.AlignLeft)
        topLayout.addWidget(otherNameLabel, 1, Qt.AlignLeft)
        
        ownNameLabel = QLabel(ownName, topWidget)
        ownPicLabel = QLabel(topWidget)
        ownPicLabel.setPixmap(QPixmap(ownPicFile).scaled(24,24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        topLayout.addWidget(ownNameLabel, 1, Qt.AlignRight)
        topLayout.addWidget(ownPicLabel, 0, Qt.AlignRight)
        
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
        
    def addOwnMessage(self, msgID, msg, messageState=None, toolTip=None, scroll=True):
        self._model.addOwnMessage(msgID, msg, messageState, toolTip)
        self.entry.clear()
        self.entry.setEnabled(True)
        self.entry.setFocus(Qt.OtherFocusReason)
        if scroll:
            self.scrollToEnd()
        
    def addOtherMessage(self, msg, scroll=True):
        self._model.addOtherMessage(msg)
        if scroll:
            self.scrollToEnd(force=False)
        
    def delayedDelivery(self, msgID):
        return self._model.messageDelivered(msgID)
        
    def canClose(self):
        return self.entry.isEnabled()
        
    def getOwnIcon(self):
        return self._ownIcon    
    def setOwnIcon(self, icon):
        self._ownIcon = icon

    def getOtherIcon(self):
        return self._otherIcon        
    def setOtherIcon(self, icon):
        self._otherIcon = icon
        
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
        self.entry.setEnabled(False)

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
    from lunchinator.iface_plugins import iface_gui_plugin
    
    def createTable(window):
        ownIcon = get_settings().get_resource("images", "me.png")
        otherIcon = get_settings().get_resource("images", "lunchinator.png")
        tw = ChatWidget(window, "Me", "Other Guy", ownIcon, otherIcon, "ID")
        tw.addOwnMessage(0, "foo<br> <a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a> Nachrichten", ChatMessagesModel.MESSAGE_STATE_NOT_DELIVERED)
        tw.addOtherMessage("<a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a>")
        tw.addOtherMessage("foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("<a href=\"mailto:info@lunchinator.de\">Lunchinator Mail</a>")
        tw.addOwnMessage(1, "bar", ChatMessagesModel.MESSAGE_STATE_ERROR)
        tw.addOwnMessage(2, "foo asdkfjh askjdfh kjash d asldfj alksdjf lkjsad fhasgdjwegr jhgasdkfjhg wjekrhg ajskhdgrkjwheg rkjhwg jkhewg r kawjhegr jkhwegr jkhweg fkjh wekjrh klahsdflkjah welkrh kasjdh fklahwe rklhaskdljfh lkajsehr lkjsahd rlkjhsd lkrjh sakldjhr lkajsh")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("foo")
        tw.addOwnMessage(3, "bar")
        return tw
        
    iface_gui_plugin.run_standalone(createTable)
    
