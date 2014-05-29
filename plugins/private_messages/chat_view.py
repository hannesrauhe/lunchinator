from PyQt4.QtGui import QTreeView, QWidget, QVBoxLayout, QSizePolicy,\
    QFrame, QStandardItemModel, QStandardItem, QIcon, QHeaderView
from PyQt4.QtCore import Qt, QSize, QVariant
from lunchinator import convert_string, get_settings
from lunchinator.history_line_edit import HistoryTextEdit
from private_messages.message_item_delegate import MessageItemDelegate

class ChatWidget(QWidget):
    PREFERRED_WIDTH = 400
    
    def __init__(self, parent, triggeredEvent, ownIcon, otherIcon):
        super(ChatWidget, self).__init__(parent)
        
        self.externalEvent = triggeredEvent
        
        self._ownIcon = ownIcon
        self._otherIcon = otherIcon
        
        self._model = QStandardItemModel(self)
        self._model.setColumnCount(3)
        
        self.table = QTreeView(self)
        self.table.setIconSize(QSize(32,32))
        self.table.setModel(self._model)
        self.table.header().setStretchLastSection(False)
        self.table.header().setResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 35)
        self.table.setColumnWidth(2, 35)
        
        self.table.setItemDelegate(MessageItemDelegate(self.table))
        self.table.setStyleSheet("background-color:transparent;")
        self.table.setSelectionMode(QTreeView.NoSelection)
        self.table.setSortingEnabled(False)
        self.table.setHeaderHidden(True)
        self.table.setAlternatingRowColors(False)
        self.table.setIndentation(0)
        
        self.table.setFrameShadow(QFrame.Plain)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setFocusPolicy(Qt.NoFocus)
        
        # TODO option to change behavior
        self.entry = HistoryTextEdit(self, True)
        tableLayout = QVBoxLayout(self)
        tableLayout.addWidget(self.table)
        tableLayout.addWidget(self.entry)
        
        self.entry.returnPressed.connect(self.eventTriggered)
        
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
    
