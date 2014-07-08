from PyQt4.QtGui import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,\
    QFrame
from PyQt4.QtCore import Qt, QSize
from lunchinator import convert_string
from lunchinator.history_line_edit import HistoryLineEdit, HistoryTextEdit
from lunchinator.utilities import getPlatform, PLATFORM_MAC

class TableWidget(QWidget):
    PREFERRED_WIDTH = 400
    
    _TABLE_OBJ_NAME = u"__table_widget_table"
    
    def __init__(self, parent, buttonText, triggeredEvent, sortedColumn=None, ascending=True, placeholderText="", useTextEdit=False, sortingEnabled=True):
        super(TableWidget, self).__init__(parent)
        
        self.externalEvent = triggeredEvent
        
        # create HBox in VBox for each table
        # Create message table
        bottomWidget = QWidget(self)
        tableBottomLayout = QHBoxLayout(bottomWidget)
        if getPlatform() == PLATFORM_MAC:
            tableBottomLayout.setContentsMargins(10, 0, 10, 0)
        else:
            tableBottomLayout.setContentsMargins(10, 0, 10, 5)
        
        self.table = QTreeView(self)
        self.table.setSortingEnabled(sortingEnabled)
        self.table.setHeaderHidden(False)
        self.table.setAlternatingRowColors(True)
        self.table.setIndentation(0)
        self.table.setUniformRowHeights(True)
        self.table.setObjectName(self._TABLE_OBJ_NAME)
        
        self.table.setFrameShape(QFrame.StyledPanel)
        if getPlatform() == PLATFORM_MAC:
            self.table.setStyleSheet("QFrame#%s{border-width: 1px; border-top-style: none; border-right-style: none; border-bottom-style: solid; border-left-style: none; border-color:palette(mid)}" % self._TABLE_OBJ_NAME);
        if sortedColumn != None:
            self.table.sortByColumn(sortedColumn, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
        
        if useTextEdit:
            self.entry = HistoryTextEdit(self)
        else:
            self.entry = HistoryLineEdit(self, placeholderText)
        tableBottomLayout.addWidget(self.entry)
        button = QPushButton(buttonText, self)
        button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        tableBottomLayout.addWidget(button, 0, Qt.AlignBottom if useTextEdit else Qt.AlignCenter)
        
        tableLayout = QVBoxLayout(self)
        tableLayout.setSpacing(5)
        tableLayout.setContentsMargins(0, 0, 0, 0)
        tableLayout.addWidget(self.table)
        tableLayout.addWidget(bottomWidget)
        
        self.entry.returnPressed.connect(self.eventTriggered)
        button.clicked.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def eventTriggered(self):
        text = convert_string(self.entry.text())
        ret_val = self.externalEvent(text)
        if ret_val != False:
            self.entry.clear()
    
    def sizeHint(self):
        sizeHint = QWidget.sizeHint(self)
        return QSize(self.PREFERRED_WIDTH, sizeHint.height())
        
    def setModel(self, model):
        self.table.setModel(model)
        
    def setColumnWidth(self, column, width):
        self.table.setColumnWidth(column, width)
        
    def getTable(self):
        return self.table
        
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    from PyQt4.QtGui import QStandardItemModel
    def table(window):
        tw = TableWidget(window, "Enter", foo, useTextEdit=False)
        model = QStandardItemModel(tw)
        model.setHorizontalHeaderLabels([u"foo", u"bar"])
        tw.setModel(model)
        return tw
    def foo(text):
        print text
    iface_gui_plugin.run_standalone(table)
    
