from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QApplication, QTextDocument,\
    QStyle, QAbstractTextDocumentLayout, QPalette, QItemDelegate,\
    QStyleOptionViewItem
from PyQt4.QtCore import Qt, QSize, QString, QEvent, QPointF, QPoint
import webbrowser

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

    def paint(self, painter, option, modelIndex):
        optionV4 = QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, modelIndex)
        
        rightAligned = (int(optionV4.displayAlignment) & int(Qt.AlignRight)) != 0
        selected = (int(optionV4.state) & int(QStyle.State_Selected)) != 0
        
        if rightAligned:
            optionV4.decorationPosition = QStyleOptionViewItem.Right
        
        text = QString(optionV4.text)
        if not text:
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
            return super(MessageItemDelegate, self).sizeHint(option, index)
    
        doc = QTextDocument()
        doc.setHtml(optionV4.text)
        doc.setTextWidth(optionV4.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())