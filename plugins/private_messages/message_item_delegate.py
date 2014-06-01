from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QApplication, QTextDocument,\
    QStyle, QAbstractTextDocumentLayout, QPalette, QItemDelegate,\
    QStyleOptionViewItem, QBrush, QColor, QGradient, QLinearGradient, QPainter,\
    QTextEdit, QHBoxLayout, QFrame, QSizePolicy
from PyQt4.QtCore import Qt, QSize, QString, QEvent, QPointF, QPoint, QRect,\
    QRectF, QSizeF
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
        
        self.closeEditor.connect(self._editorClosing)
    
    def setEditIndex(self, modelIndex):
        self._editIndex = modelIndex
        
    def getEditIndex(self):
        return self._editIndex
        
    def _editorClosing(self, _editor, _hint):
        self._editor = None
        self.setEditIndex(None)
        
    def getEditor(self):
        return self._editor
    
    def createEditor(self, parent, option, modelIndex):
        self.setEditIndex(modelIndex)
        
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, modelIndex)
        
        rightAligned = (int(optionV4.displayAlignment) & int(Qt.AlignRight)) != 0
        if rightAligned:
            optionV4.decorationPosition = QStyleOptionViewItem.Right
            
        text = QString(optionV4.text)
        doc = QTextDocument()
        doc.setHtml(text)
        
        doc.setTextWidth(optionV4.rect.width())
    
        editorWidget = QWidget(parent)
        editorLayout = QHBoxLayout(editorWidget)
        editorLayout.setContentsMargins(0, 0, 0, 0)
        editor = ItemEditor(doc, QSize(doc.idealWidth(), doc.size().height()), rightAligned, editorWidget)
        editorLayout.addWidget(editor, 0, Qt.AlignRight if rightAligned else Qt.AlignLeft)
        
        self._editor = editorWidget
        return editorWidget
    
    def setModelData(self, *_args, **_kwargs):
        pass
    
    def paint(self, painter, option, modelIndex):
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, modelIndex)
        
        rightAligned = (int(optionV4.displayAlignment) & int(Qt.AlignRight)) != 0
        selected = (int(optionV4.state) & int(QStyle.State_Selected)) != 0
        editing = self._editIndex == modelIndex
        
        if rightAligned:
            optionV4.decorationPosition = QStyleOptionViewItem.Right
        
        text = QString(optionV4.text)
        if not text:
            option.decorationAlignment = Qt.AlignLeft
            return super(MessageItemDelegate, self).paint(painter, option, modelIndex)
    
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
            xOffset = textRect.width() - self.document.idealWidth() - 3
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
        
        painter.setRenderHint(QPainter.Antialiasing)
        if not editing:
            painter.setBrush(self._ownBrush if rightAligned else self._otherBrush)
        painter.setPen(self._ownPenColor if rightAligned else self._otherPenColor)
        painter.drawRoundedRect(QRectF(QPointF(0, 0.5),
                                       QSizeF(self.document.size().width(),
                                              self.document.size().height() - 1.)),
                                7, 7)
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        if not editing:
            self.document.documentLayout().draw(painter, ctx)
        painter.restore()

    def editorEvent(self, event, _model, option, modelIndex):
        self.initStyleOption(option, modelIndex)
        text = QString(option.text)
        if not text:
            self.parent().unsetCursor()
            return False
        
        if event.type() not in (QEvent.MouseMove, QEvent.MouseButtonRelease) \
            or not (option.state & QStyle.State_Enabled):
            return False
        
        # Get the link at the mouse position
        # (the explicit QPointF conversion is only needed for PyQt)
        pos = QPointF(event.pos() - self.lastTextPos)
        #print pos
        anchor = self.mouseOverDocument.documentLayout().anchorAt(pos)
        if anchor == "":
            textRext = QRectF(0, 0, self.mouseOverDocument.size().width(), self.mouseOverDocument.size().height())
            if textRext.contains(pos):
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
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        
        if not optionV4.text:
            return super(MessageItemDelegate, self).sizeHint(option, index)
    
        doc = QTextDocument()
        doc.setHtml(optionV4.text)
        doc.setTextWidth(optionV4.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())