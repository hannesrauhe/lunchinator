from PyQt4.QtGui import QTreeView, QHeaderView, QFrame, QAbstractItemDelegate
from PyQt4.QtCore import Qt, QSize
from private_messages.message_item_delegate import MessageItemDelegate

class ChatMessagesView(QTreeView):
    def __init__(self, model, parent):
        super(ChatMessagesView, self).__init__(parent)
        self.setIconSize(QSize(32,32))
        self.setModel(model)
        self.header().setStretchLastSection(False)
        self.header().setResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 32)
        self.setColumnWidth(2, 32)
        
        self.setItemDelegate(MessageItemDelegate(self))
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        
        self.setSelectionMode(QTreeView.NoSelection)
        self.setSortingEnabled(False)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setIndentation(0)
        
        self.setFrameShadow(QFrame.Plain)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.column() == 1 and index != self.itemDelegate().getEditIndex():
                if self.itemDelegate().getEditor() != None:
                    self.closeEditor(self.itemDelegate().getEditor(), QAbstractItemDelegate.NoHint)
                self.itemDelegate().setEditIndex(index)
                self.edit(index)
        super(ChatMessagesView, self).mousePressEvent(event)
