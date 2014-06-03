from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QApplication, QTextDocument,\
    QStyle, QAbstractTextDocumentLayout, QPalette, QItemDelegate,\
    QStyleOptionViewItem, QBrush, QColor, QGradient, QLinearGradient, QPainter,\
    QTextEdit, QHBoxLayout, QFrame, QSizePolicy
from PyQt4.QtCore import Qt, QSize, QString, QEvent, QPointF, QPoint, QRect,\
    QRectF, QSizeF, pyqtSignal, QModelIndex
import webbrowser
from PyQt4.Qt import QWidget

class ItemEditor(QTextEdit):
    def __init__(self, document, textSize, rightAligned, parent):
        super(ItemEditor, self).__init__(parent)
        self.setDocument(document)
        self._textSize = textSize
        self.setReadOnly(True)
        
        self.viewport().setAutoFillBackground(False)
        self.setAutoFillBackground(False)
        self.setFrameShadow(QFrame.Plain)
        self.setFrameStyle(QFrame.NoFrame)
        
        self.setViewportMargins(-4 if rightAligned else 0, 0, -5, -5)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        self.setMinimumSize(textSize)
        self.setMaximumSize(textSize)
        self.setFocusPolicy(Qt.StrongFocus)
        
    def sizeHint(self):
        return self._textSize
            
class MessageItemDelegate(QStyledItemDelegate):
    def __init__(self, parentView):
        QItemDelegate.__init__(self, parentView)

        # We need that to receive mouse move events in editorEvent
        parentView.setMouseTracking(True)

        # Revert the mouse cursor when the mouse isn't over 
        # an item but still on the view widget
        parentView.viewportEntered.connect(parentView.unsetCursor)

        self.document = QTextDocument()
        self.mouseOverDocument = self.document
        self.mouseOverOption = None
        self.lastTextPos = QPoint(0, 0)
        self._editIndex = None
        self._editor = None
        
        ownGradient = QLinearGradient(0, 0, 0, 10)
        ownGradient.setColorAt(0, QColor(194, 215, 252))
        ownGradient.setColorAt(1, QColor(182, 208, 251))
        self._ownBrush = QBrush(ownGradient)
        self._ownPenColor = QColor(104, 126, 164)
        
        otherGradient = QLinearGradient(0, 0, 0, 10)
        otherGradient.setColorAt(0, QColor(236, 236, 236))
        otherGradient.setColorAt(1, QColor(200, 200, 200))
        self._otherBrush = QBrush(otherGradient)
        self._otherPenColor = QColor(153, 153, 153)
        
        self.closeEditor.connect(self.editorClosing)
    
    def setEditIndex(self, modelIndex):
        self._editIndex = modelIndex
        
    def getEditIndex(self):
        return self._editIndex
        
    def editorClosing(self, _editor, _hint):
        self._editor = None
        self.setEditIndex(None)
        
    def getEditor(self):
        return self._editor
    
    def initStyleOption(self, option, modelIndex):
        if modelIndex.column() == 1:
            # we're handling this ourselves
            option.decorationSize = QSize(0,0)
        return QStyledItemDelegate.initStyleOption(self, option, modelIndex)
    
    def createEditor(self, parent, option, modelIndex):
        self.setEditIndex(modelIndex)
        
        self.initStyleOption(option, modelIndex)
        
        rightAligned = (int(option.displayAlignment) & int(Qt.AlignRight)) != 0
        if rightAligned:
            option.decorationPosition = QStyleOptionViewItem.Right
            
        text = QString(option.text)
        doc = QTextDocument()
        doc.setHtml(text)
        
        doc.setTextWidth(option.rect.width())
        
        messageRect = self._getMessageRect(option, doc, relativeToItem=True)
    
        editorWidget = QWidget(parent)
        editor = ItemEditor(doc, QSize(doc.idealWidth(), doc.size().height()), rightAligned, editorWidget)

        pos = messageRect.topLeft()
        if rightAligned:
            pos += QPoint(4, 0)
        editor.move(pos)
        editor.resize(messageRect.size())
        
        self._editor = editorWidget
        return editorWidget
    
    def setModelData(self, *_args, **_kwargs):
        pass
    
    def _getMessageRect(self, option, doc, relativeToItem=False):
        rightAligned = (int(option.displayAlignment) & int(Qt.AlignRight)) != 0
        textRect = option.rect
        
        documentWidth = doc.idealWidth()
        if rightAligned:
            xOffset = textRect.width() - documentWidth - 3
            if not option.icon.isNull():
                xOffset -= 20
        else:
            xOffset = 3
            if not option.icon.isNull():
                xOffset += 20
        
        if doc.size().height() < 32:
            # vertically center
            yOffset = (32. - doc.size().height()) / 2 + 1
        else:
            yOffset = 0
        
        textPos = QPoint(0,0) if relativeToItem else textRect.topLeft()
        textPos += QPoint(xOffset, yOffset)
        return QRect(textPos, QSize(documentWidth, doc.size().height()))
    
    def paint(self, painter, option1, modelIndex):
        option = QStyleOptionViewItemV4(option1)
        self.initStyleOption(option, modelIndex)
        
        text = QString(option.text)
        if not text:
            option1.decorationAlignment = Qt.AlignLeft
            return super(MessageItemDelegate, self).paint(painter, option1, modelIndex)
        
        rightAligned = (int(option.displayAlignment) & int(Qt.AlignRight)) != 0
        selected = (int(option.state) & int(QStyle.State_Selected)) != 0
        editing = self._editIndex == modelIndex
    
        option.decorationPosition = Qt.AlignRight if rightAligned else Qt.AlignLeft
        
        self.document.setHtml(text)
        self.document.setTextWidth(option.rect.width())
        
        ctx = QAbstractTextDocumentLayout.PaintContext()
    
        # Highlighting text if item is selected
        if selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))
    
        # total rect for us to paint in
        textRect = option.rect
        # final rect to paint message in
        messageRect = self._getMessageRect(option, self.document)
        
        painter.save()
        
        mouseOver = (int(option.state) & int(QStyle.State_MouseOver)) != 0
        if mouseOver:
            self.mouseOverDocument = QTextDocument()
            self.mouseOverDocument.setHtml(text)
            self.mouseOverDocument.setTextWidth(option.rect.width())
            self.lastTextPos = textRect.topLeft()
            self.mouseOverOption = option
        
        
        # draw decoration
        painter.translate(textRect.topLeft())
        if not option.icon.isNull():
            if rightAligned:
                option.icon.paint(painter, textRect.size().width() - 19, 8, 16, 16, Qt.AlignCenter)
            else:
                option.icon.paint(painter, 3, 8, 16, 16, Qt.AlignCenter)
                
        # draw message
        painter.restore()
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(messageRect.topLeft())
        if not editing:
            painter.setBrush(self._ownBrush if rightAligned else self._otherBrush)
        painter.setPen(self._ownPenColor if rightAligned else self._otherPenColor)
        painter.drawRoundedRect(QRectF(QPointF(0, 0.5),
                                       QSizeF(self.document.idealWidth(),
                                              self.document.size().height() - 1.)),
                                7, 7)
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        if not editing:
            self.document.documentLayout().draw(painter, ctx)
        painter.restore()

    startEditing = pyqtSignal(QModelIndex)

    def shouldStartEditAt(self, eventPos, modelIndex):
        option = QStyleOptionViewItemV4()
        option.initFrom(self.parent())
        option.rect.setHeight(32)
        self.initStyleOption(option, modelIndex)
        
        messageRect = self._getMessageRect(self.mouseOverOption, self.mouseOverDocument)
        anchor = self.mouseOverDocument.documentLayout().anchorAt(eventPos - messageRect.topLeft())
        if anchor != "":
            return False
        
        return messageRect.contains(eventPos)

    def editorEvent(self, event, _model, option, modelIndex):
        self.initStyleOption(option, modelIndex)
        text = QString(option.text)
        if not text:
            self.parent().unsetCursor()
            return False
        
        if event.type() not in (QEvent.MouseMove, QEvent.MouseButtonRelease, QEvent.MouseButtonPress) \
            or not (option.state & QStyle.State_Enabled):
            return False
        
        # Get the link at the mouse position
        pos = event.pos()
        messageRect = self._getMessageRect(option, self.mouseOverDocument)
        anchor = self.mouseOverDocument.documentLayout().anchorAt(pos - messageRect.topLeft())
        if anchor == "":
            if messageRect.contains(pos):
                self.parent().setCursor(Qt.IBeamCursor)
            else:
                self.parent().unsetCursor()
        else:
            self.parent().setCursor(Qt.PointingHandCursor)               
            if event.type() == QEvent.MouseButtonRelease:
                webbrowser.open(anchor)
                return True 
        return False

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)
        
        if not option.text:
            return super(MessageItemDelegate, self).sizeHint(option, index)
    
        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), max(32, doc.size().height()))