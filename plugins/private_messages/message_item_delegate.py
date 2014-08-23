from private_messages.chat_messages_model import ChatMessagesModel
from lunchinator import convert_string
from lunchinator.utilities import formatTime

from PyQt4.QtGui import QStyledItemDelegate, QStyleOptionViewItemV4, QTextDocument,\
    QStyle, QAbstractTextDocumentLayout, QPalette,\
    QBrush, QColor, QLinearGradient, QPainter,\
    QTextEdit, QFrame, QSizePolicy, QIcon, QFont
from PyQt4.QtCore import Qt, QSize, QString, QEvent, QPointF, QPoint, QRect,\
    QRectF, QSizeF, pyqtSignal, QModelIndex, QMetaType
from PyQt4.Qt import QWidget

import webbrowser
from time import localtime
from lunchinator.log.logging_slot import loggingSlot

class ItemEditor(QTextEdit):
    def __init__(self, text, width, parent):
        super(ItemEditor, self).__init__(parent)
        self.setReadOnly(True)
        
        self.viewport().setAutoFillBackground(False)
        self.setAutoFillBackground(False)
        self.setFrameShadow(QFrame.Plain)
        self.setFrameStyle(QFrame.NoFrame)
        
        self.setViewportMargins(0, 0, -5, -5)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.document().setHtml(text)
        self.document().setTextWidth(width)
        
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        textSize = QSize(self.document().idealWidth(), self.document().size().height())
        self.setMinimumSize(textSize)
        self.setMaximumSize(textSize)
        self.setFocusPolicy(Qt.StrongFocus)
        
    def sizeHint(self):
        return self._textSize
    
class EditorWidget(QWidget):
    def __init__(self, parent):
        super(EditorWidget, self).__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        self._itemEditor = None
    
    def focusInEvent(self, event):
        if self._itemEditor != None:
            event.ignore()
            self._itemEditor.setFocus(event.reason())
        else:
            # should not happen
            event.accept()
        
    def setItemEditor(self, itemEditor):
        self._itemEditor = itemEditor
            
class MessageItemDelegate(QStyledItemDelegate):
    def __init__(self, parentView, logger, column=None, margin=50):
        super(MessageItemDelegate, self).__init__(parentView)

        self.logger = logger
        # We need that to receive mouse move events in editorEvent
        parentView.setMouseTracking(True)

        # Revert the mouse cursor when the mouse isn't over 
        # an item but still on the view widget
        parentView.viewportEntered.connect(self.unsetParentCursor)

        self.document = QTextDocument()
        self.mouseOverDocument = self.document
        self.mouseOverDocumentRow = -1
        self.mouseOverOption = None
        self.lastTextPos = QPoint(0, 0)
        self._editIndex = None
        self._editor = None
        self._column = column
        self._margin = margin
        
        ownGradient = QLinearGradient(0, 0, 0, 10)
        ownGradient.setColorAt(0, QColor(229, 239, 254))
        ownGradient.setColorAt(1, QColor(182, 208, 251))
        self._ownBrush = QBrush(ownGradient)
        self._ownPenColor = QColor(104, 126, 164)
        
        otherGradient = QLinearGradient(0, 0, 0, 10)
        otherGradient.setColorAt(0, QColor(248, 248, 248))
        otherGradient.setColorAt(1, QColor(200, 200, 200))
        self._otherBrush = QBrush(otherGradient)
        self._otherPenColor = QColor(153, 153, 153)
        
        self._timeFont = QFont("default", 12, QFont.Bold)
        
        self.closeEditor.connect(self.editorClosing)
        
        self._rowHeights = {}
        
    @loggingSlot()
    def unsetParentCursor(self):
        self.parent().unsetCursor()
        
    def setEditIndex(self, modelIndex):
        self._editIndex = modelIndex
        
    def getEditIndex(self):
        return self._editIndex
        
    @loggingSlot(QWidget, int)
    def editorClosing(self, _editor, _hint):
        self._editor = None
        self.setEditIndex(None)
        
    def getEditor(self):
        return self._editor
    
    def createEditor(self, parent, option_, modelIndex):
        self.setEditIndex(modelIndex)
        
        option = QStyleOptionViewItemV4(option_)
        self.initStyleOption(option, modelIndex)
        
        text = QString(option.text)
    
        editorWidget = EditorWidget(parent)
        editor = ItemEditor(text, self._preferredMessageWidth(option.rect.width()), editorWidget)
        editorWidget.setItemEditor(editor)

        messageRect = self._getMessageRect(option, editor.document(), modelIndex, relativeToItem=True)
        pos = messageRect.topLeft()
        editor.move(pos)
        editor.resize(messageRect.size())
        
        self._editor = editorWidget
        return editorWidget
    
    def setModelData(self, *_args, **_kwargs):
        pass
    
    def _preferredMessageWidth(self, textRectWidth):
        return textRectWidth - self._margin
    
    def _getMessageRect(self, option, doc, modelIndex, relativeToItem=False):
        rightAligned = modelIndex.data(ChatMessagesModel.OWN_MESSAGE_ROLE).toBool()
        statusIcon = modelIndex.data(ChatMessagesModel.STATUS_ICON_ROLE)
        hasStatusIcon = statusIcon != None and not statusIcon.isNull()
        textRect = option.rect
        
        documentWidth = doc.idealWidth()
        if rightAligned:
            xOffset = textRect.width() - documentWidth - 3
            if hasStatusIcon:
                xOffset -= 20
        else:
            xOffset = 3
            if hasStatusIcon:
                xOffset += 20
        
        height = doc.size().height()
        if modelIndex.row() not in self._rowHeights:
            self._rowHeights[modelIndex.row()] = height
        elif self._rowHeights[modelIndex.row()] != height:
            self._rowHeights[modelIndex.row()] = height
            self.sizeHintChanged.emit(modelIndex)
            
        if height < 32:
            # vertically center
            yOffset = (32. - height) / 2 + 1
        else:
            yOffset = 0
        
        textPos = QPoint(0,0) if relativeToItem else textRect.topLeft()
        textPos += QPoint(xOffset, yOffset)
        return QRect(textPos, QSize(documentWidth, height))
    
    def _paintTime(self, painter, option, modelIndex):
        if modelIndex.column() != 1:
            return
        # total rect for us to paint in
        textRect = option.rect
        
        rtime, _ok = modelIndex.data(Qt.DisplayRole).toDouble()
        timeString = formatTime(localtime(rtime))
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(textRect.topLeft())
        painter.setFont(self._timeFont)
        textWidth = painter.fontMetrics().width(timeString)
        painter.drawText((textRect.size().width() - textWidth) / 2, 13, timeString)
        painter.restore()
    
    def paint(self, painter, option1, modelIndex):
        if self._column is not None and modelIndex.column() != self._column:
            return super(MessageItemDelegate, self).paint(painter, option1, modelIndex)
        
        option = QStyleOptionViewItemV4(option1)
        self.initStyleOption(option, modelIndex)
        
        if modelIndex.data(Qt.DisplayRole).type() == QMetaType.Double:
            # this is a time item
            self._paintTime(painter, option, modelIndex)
            return

        text = QString(option.text)
        if not text:
            option1.decorationAlignment = Qt.AlignLeft
            return super(MessageItemDelegate, self).paint(painter, option1, modelIndex)
        
        rightAligned = modelIndex.data(ChatMessagesModel.OWN_MESSAGE_ROLE).toBool()
        selected = (int(option.state) & int(QStyle.State_Selected)) != 0
        editing = self._editIndex == modelIndex
    
        self.document.setHtml(text)
        self.document.setTextWidth(self._preferredMessageWidth(option.rect.width()))
        
        ctx = QAbstractTextDocumentLayout.PaintContext()
    
        # Highlighting text if item is selected
        if selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))
    
        # total rect for us to paint in
        textRect = option.rect
        # final rect to paint message in
        messageRect = self._getMessageRect(option, self.document, modelIndex)
        
        painter.save()
        
        mouseOver = (int(option.state) & int(QStyle.State_MouseOver)) != 0
        if mouseOver:
            self.mouseOverDocument = QTextDocument()
            self.mouseOverDocument.setHtml(text)
            self.mouseOverDocument.setTextWidth(self._preferredMessageWidth(option.rect.width()))
            self.mouseOverDocumentRow = modelIndex.row()
            self.lastTextPos = textRect.topLeft()
            self.mouseOverOption = option
        
        # draw decoration
        painter.translate(textRect.topLeft())
        statusIcon = modelIndex.data(ChatMessagesModel.STATUS_ICON_ROLE)
        if statusIcon != None and not statusIcon.isNull():
            statusIcon = QIcon(statusIcon)
            if rightAligned:
                statusIcon.paint(painter, textRect.size().width() - 19, 8, 16, 16, Qt.AlignCenter)
            else:
                statusIcon.paint(painter, 3, 8, 16, 16, Qt.AlignCenter)
                
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
        
        if modelIndex.row() != self.mouseOverDocumentRow:
            # TODO reset document
            self.logger.warning("shouldStartEditAt(): wrong mouse over document")
            return False
        messageRect = self._getMessageRect(self.mouseOverOption, self.mouseOverDocument, modelIndex)
        anchorPos = QPointF(eventPos) - QPointF(messageRect.topLeft())
        anchor = self.mouseOverDocument.documentLayout().anchorAt(anchorPos)
        if anchor != "":
            return False
        
        return messageRect.contains(eventPos)

    def editorEvent(self, event, _model, option_, modelIndex):
        if self._column and modelIndex.column() != self._column:
            return False
        option = QStyleOptionViewItemV4(option_)
        self.initStyleOption(option, modelIndex)
        text = QString(option.text)
        if not text:
            self.parent().unsetCursor()
            return False
        
        if event.type() not in (QEvent.MouseMove, QEvent.MouseButtonRelease, QEvent.MouseButtonPress) \
            or not (option.state & QStyle.State_Enabled):
            return False
        
        if modelIndex.row() != self.mouseOverDocumentRow:
            return False
        
        # Get the link at the mouse position
        pos = event.pos()
        messageRect = self._getMessageRect(option, self.mouseOverDocument, modelIndex)
        anchor = convert_string(self.mouseOverDocument.documentLayout().anchorAt(QPointF(pos) - QPointF(messageRect.topLeft())))
        if anchor == "":
            if messageRect.contains(pos):
                self.parent().setCursor(Qt.IBeamCursor)
            else:
                self.parent().unsetCursor()
        else:
            self.parent().setCursor(Qt.PointingHandCursor)               
            if event.type() == QEvent.MouseButtonRelease:
                if anchor.startswith(u"www."):
                    anchor = u"http://" + anchor
                webbrowser.open(anchor)
                return True 
        return False

    def sizeHint(self, option1, index):
        # option.rect is a zero rect
        width = self.parent().columnWidth(index.column())
        
        if index.data(Qt.DisplayRole).type() == QMetaType.Double:
            return QSize(width, 18)
        
        option = QStyleOptionViewItemV4(option1)
        self.initStyleOption(option, index)
        
        if not option.text:
            iconSize = option.icon.actualSize(QSize(32, 32))
            return QSize(32, max(32, iconSize.height() + 4))
        
        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.setTextWidth(self._preferredMessageWidth(width))
        
        return QSize(doc.idealWidth(), max(32, doc.size().height() + 4))
    
