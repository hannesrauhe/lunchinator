from PyQt4.QtGui import QTreeView, QHeaderView, QFrame, QAbstractItemDelegate,\
    QPalette, QColor
from PyQt4.QtCore import Qt, QSize
from private_messages.message_item_delegate import MessageItemDelegate
from lunchinator.log.logging_slot import loggingSlot

class ChatMessagesView(QTreeView):
    def __init__(self, model, parent, logger):
        super(ChatMessagesView, self).__init__(parent)
        self.logger = logger
        
        self.setIconSize(QSize(32,32))
        self.setModel(model)
        self.header().setStretchLastSection(False)
        self.header().setResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 32)
        self.setColumnWidth(2, 32)
        
        self.setItemDelegate(MessageItemDelegate(self, self.logger))
        self.setAutoFillBackground(False)
        
        pal = QPalette(self.palette())
        pal.setColor(QPalette.Base, QColor(0,0,0,0));
        self.setPalette(pal);
        
        self.viewport().setAutoFillBackground(False)
        
        self.setSelectionMode(QTreeView.NoSelection)
        self.setSortingEnabled(False)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setIndentation(0)
        
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.verticalScrollBar().rangeChanged.connect(self._scrollRangeChanged)
        self.verticalScrollBar().valueChanged.connect(self._scrollValueChanged)
        
        self.setFrameShadow(QFrame.Plain)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        
        self._scrollToEnd = True
        self._scrollMax = 0
        
    @loggingSlot(int)
    def _scrollValueChanged(self, val):
        self._scrollToEnd = val >= self._scrollMax
        
    @loggingSlot(int, int)
    def _scrollRangeChanged(self, _minV, maxV):
        self._scrollMax = maxV
        if self._scrollToEnd:
            self.verticalScrollBar().setValue(self._scrollMax)
            
    def setScrollToEnd(self, scroll):
        self._scrollToEnd = scroll
        
    def stopEditing(self):
        if self.itemDelegate().getEditor() != None:
            self.closeEditor(self.itemDelegate().getEditor(), QAbstractItemDelegate.NoHint)
            self.itemDelegate().editorClosing(self.itemDelegate().getEditor(), QAbstractItemDelegate.NoHint)
            
    def focusInEvent(self, _event):
        # I definitely don't want the focus
        self.clearFocus()
        self.parent().setFocus(Qt.OtherFocusReason)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.column() == 1 and self.itemDelegate().shouldStartEditAt(event.pos(), index):
                # do not start editing if already editing
                if index != self.itemDelegate().getEditIndex():
                    self.stopEditing()
                    self.itemDelegate().setEditIndex(index)
                    self.edit(index)
            else:
                # clicked somewhere else -> stop editing
                self.stopEditing()
        super(ChatMessagesView, self).mousePressEvent(event)
