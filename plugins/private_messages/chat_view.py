from PyQt4.QtGui import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,\
    QFrame, QStandardItemModel, QStandardItem, QIcon, QHeaderView,\
    QStyledItemDelegate, QStyleOptionViewItemV4, QApplication, QTextDocument,\
    QStyle, QAbstractTextDocumentLayout, QPalette, QFontMetrics, QItemDelegate,\
    QCursor, QStyleOptionViewItem
from PyQt4.QtCore import Qt, QSize, QVariant, QString, QEvent, QPointF, QPoint,\
    QRect
from lunchinator import convert_string, get_settings
from lunchinator.history_line_edit import HistoryTextEdit
import webbrowser

class LinkItemDelegate(QStyledItemDelegate):
    def __init__(self, parentView):
        QItemDelegate.__init__(self, parentView)

        # We need that to receive mouse move events in editorEvent
        parentView.setMouseTracking(True)

        # Revert the mouse cursor when the mouse isn't over 
        # an item but still on the view widget
        parentView.viewportEntered.connect(parentView.unsetCursor)

        self.document = QTextDocument()
        self.mouseOverDocument = self.document
        self.lastTextPos = QPoint(0, 0)

    def paint(self, painter, option, modelIndex):
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, modelIndex)
        
        rightAligned = (int(optionV4.displayAlignment) & int(Qt.AlignRight)) != 0
        selected = (int(optionV4.state) & int(QStyle.State_Selected)) != 0
        
        if rightAligned:
            optionV4.decorationPosition = QStyleOptionViewItem.Right
        
        text = QString(optionV4.text)
        if not text:
            return super(LinkItemDelegate, self).paint(painter, option, modelIndex)
    
        style = optionV4.widget.style() if optionV4.widget else QApplication.style()
    
        self.document.setHtml(text)
    
        # Painting item without text
        optionV4.text = QString()
        style.drawControl(QStyle.CE_ItemViewItem, optionV4, painter);
        
        ctx = QAbstractTextDocumentLayout.PaintContext()
    
        # Highlighting text if item is selected
        if selected:
            ctx.palette.setColor(QPalette.Text, optionV4.palette.color(QPalette.Active, QPalette.HighlightedText))
    
        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, optionV4)
        
        painter.save()
        
        if rightAligned:
            xOffset = textRect.width() - self.document.idealWidth()
        else:
            xOffset = 0
        
        if self.document.size().height() < textRect.height():
            yOffset = (float(textRect.height()) - self.document.size().height()) / 2
        else:
            yOffset = 0
        
        textPos = textRect.topLeft() + QPoint(xOffset, yOffset)
        
        mouseOver = (int(option.state) & int(QStyle.State_MouseOver)) != 0
        if mouseOver:
            self.mouseOverDocument = QTextDocument()
            self.mouseOverDocument.setHtml(text)
            self.lastTextPos = textPos
        
        painter.translate(textPos)
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.document.documentLayout().draw(painter, ctx)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() not in [QEvent.MouseMove, QEvent.MouseButtonRelease] \
            or not (option.state & QStyle.State_Enabled):
            return False
        
        # Get the link at the mouse position
        # (the explicit QPointF conversion is only needed for PyQt)
        pos = QPointF(event.pos() - self.lastTextPos)
        #print pos
        anchor = self.mouseOverDocument.documentLayout().anchorAt(pos)
        if anchor == "":
            self.parent().unsetCursor()
        else:
            self.parent().setCursor(Qt.PointingHandCursor)               
            if event.type() == QEvent.MouseButtonRelease:
                webbrowser.open(anchor)
                return True 
        return False

    def sizeHint(self, option, index):
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        
        if not optionV4.text:
            return super(LinkItemDelegate, self).sizeHint(option, index)
    
        doc = QTextDocument()
        doc.setHtml(optionV4.text)
        doc.setTextWidth(optionV4.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())

class ChatWidget(QWidget):
    PREFERRED_WIDTH = 400
    
    def __init__(self, parent, triggeredEvent, ownIcon, otherIcon):
        super(ChatWidget, self).__init__(parent)
        
        self.externalEvent = triggeredEvent
        
        self._ownIcon = ownIcon
        self._otherIcon = otherIcon
        
        # create HBox in VBox for each table
        # Create message table
        tableBottomLayout = QHBoxLayout()
        
        self._model = QStandardItemModel(self)
        self._model.setColumnCount(3)
        
        self.table = QTreeView(self)
        self.table.setIconSize(QSize(32,32))
        self.table.setModel(self._model)
        self.table.header().setStretchLastSection(False)
        self.table.header().setResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 35)
        self.table.setColumnWidth(2, 35)
        
        self.table.setItemDelegate(LinkItemDelegate(self.table))
        self.table.setStyleSheet("background-color:transparent;")
        self.table.setSelectionMode(QTreeView.NoSelection)
        self.table.setSortingEnabled(False)
        self.table.setHeaderHidden(True)
        self.table.setAlternatingRowColors(False)
        self.table.setIndentation(0)
        
        self.table.setFrameShadow(QFrame.Plain)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setFocusPolicy(Qt.NoFocus)
        
        
        self.entry = HistoryTextEdit(self)
        tableBottomLayout.addWidget(self.entry)
        button = QPushButton(u"Send", self)
        button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        tableBottomLayout.addWidget(button, 0, Qt.AlignBottom)
        
        tableLayout = QVBoxLayout(self)
        tableLayout.addWidget(self.table)
        tableLayout.addLayout(tableBottomLayout)
        
        self.entry.returnPressed.connect(self.eventTriggered)
        button.clicked.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def _createIconItem(self, icon):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(QVariant(icon), Qt.DecorationRole)
        item.setData(QSize(32, 32), Qt.SizeHintRole)
        return item
        
    def _createMessageIcon(self, msg, alignRight):
        item = QStandardItem()
        item.setEditable(False)
        item.setData(msg, Qt.DisplayRole)
        item.setData(Qt.AlignHCenter | (Qt.AlignRight if alignRight else Qt.AlignLeft),
                     Qt.TextAlignmentRole)
        return item
    
    def _createEmptyItem(self):
        item = QStandardItem()
        item.setEditable(False)
        return item
        
    def addOwnMessage(self, msg):
        self._model.appendRow([self._createEmptyItem(),
                               self._createMessageIcon(msg, True),
                               self._createIconItem(self._ownIcon)])
        
    def addOtherMessage(self, msg):
        self._model.appendRow([self._createIconItem(self._otherIcon),
                               self._createMessageIcon(msg, False),
                               self._createEmptyItem()])
        
    def setOwnIcon(self, icon):
        self._ownIcon = icon
        
    def setOtherIcon(self, icon):
        self._otherIcon = icon
        
    def eventTriggered(self):
        text = convert_string(self.entry.text())
        ret_val = self.externalEvent(text)
        if ret_val != False:
            self.entry.clear()
    
    def sizeHint(self):
        sizeHint = QWidget.sizeHint(self)
        return QSize(self.PREFERRED_WIDTH, sizeHint.height())
        
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    def foo(text):
        print text
    
    def createTable(window):
        ownIcon = QIcon(get_settings().get_resource("images", "mini_breakfast.png"))
        otherIcon = QIcon(get_settings().get_resource("images", "lunchinator.png"))
        tw = ChatWidget(window, foo, ownIcon, otherIcon)
        tw.addOwnMessage("<p align=right>foo<br> <a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a> Nachrichten</p>")
        tw.addOtherMessage("<a href=\"http://www.tagesschau.de/\">ARD Tagesschau</a>")
        return tw
        
    iface_gui_plugin.run_standalone(createTable)
    
