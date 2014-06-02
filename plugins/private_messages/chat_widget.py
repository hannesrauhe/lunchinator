from PyQt4.QtGui import QWidget, QVBoxLayout, QSizePolicy,\
    QFrame, QStandardItemModel, QStandardItem, QIcon, QHBoxLayout,\
    QLabel, QPixmap, QTextCharFormat, QTextCursor
from PyQt4.QtCore import Qt, QSize, QVariant, pyqtSignal, QRegExp
from lunchinator import convert_string, get_settings
from lunchinator.history_line_edit import HistoryTextEdit
from private_messages.chat_messages_view import ChatMessagesView
from xml.etree import ElementTree

class ChatWidget(QWidget):
    MESSAGE_STATE_OK = None
    MESSAGE_STATE_WARNING = 1
    MESSAGE_STATE_ERROR = 2
    
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
        self._model = QStandardItemModel(self)
        self._model.setColumnCount(3)
        
    def _initMessageTable(self):
        self.table = ChatMessagesView(self._model, self)
        
    def _createIconItem(self, icon):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(icon), Qt.DecorationRole)
        item.setData(QSize(32, 32), Qt.SizeHintRole)
        return item
        
    def _createMessageItem(self, msg, alignRight, messageState=None, toolTip=None):
        item = QStandardItem()
        item.setEditable(True)
        item.setData(msg, Qt.DisplayRole)
        
        if messageState == self.MESSAGE_STATE_WARNING:
            item.setData(QVariant(self._warnIcon), Qt.DecorationRole)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(self._errIcon), Qt.DecorationRole)
        
        if toolTip:
            item.setData(QVariant(toolTip), Qt.ToolTipRole)
        elif messageState == self.MESSAGE_STATE_ERROR:
            item.setData(QVariant(u"Unknown error, message could not be delivered."), Qt.ToolTipRole)
        item.setData(Qt.AlignHCenter | (Qt.AlignRight if alignRight else Qt.AlignLeft),
                     Qt.TextAlignmentRole)
        return item
    
    def _createEmptyItem(self):
        item = QStandardItem()
        item.setEditable(False)
        return item
        
    def addOwnMessage(self, msg, messageState=None, toolTip=None):
        self._model.appendRow([self._createEmptyItem(),
                               self._createMessageItem(msg, True, messageState, toolTip),
                               self._createIconItem(self._ownIcon)])
        self.entry.clear()
        self.entry.setEnabled(True)
        
    def addOtherMessage(self, msg):
        self._model.appendRow([self._createIconItem(self._otherIcon),
                               self._createMessageItem(msg, False),
                               self._createEmptyItem()])
        
    def setOwnIcon(self, icon):
        self._ownIcon = icon
        
    def setOtherIcon(self, icon):
        self._otherIcon = icon
        
    def eventTriggered(self):
        self._detectHyperlinks()
        text = self._cleanHTML(convert_string(self.entry.toHtml()))
        self.sendMessage.emit(self._otherID, text)
        self.entry.setEnabled(False)

    def _cleanHTML(self, html):
        # only body, no paragraph attributes
        cleaned = u""
        e = ElementTree.fromstring(html)
        body = e.iter("html").next().iter("body").next()
        for p in body.iter("p"):
            if not p.text:
                cleaned += u"<p/>"
            else:
                cleaned += u"<p>%s</p>" % p.text
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
        self._insertAnchors(cursor, plainText, self._URI_MATCHER, lambda uri : uri)
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
        tw.addOwnMessage("foo<br> <a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a> Nachrichten", ChatWidget.MESSAGE_STATE_WARNING, "Not delivered yet.")
        tw.addOtherMessage("<a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a>")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("<a href=\"mailto:info@lunchinator.de\">Lunchinator Mail</a>")
        tw.addOwnMessage("bar", ChatWidget.MESSAGE_STATE_ERROR)
        tw.addOtherMessage("foo")
        tw.addOtherMessage("foo")
        tw.addOtherMessage("foo")
        tw.addOwnMessage("bar")
        return tw
        
    iface_gui_plugin.run_standalone(createTable)
    
