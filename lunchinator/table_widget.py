from PySide.QtGui import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PySide.QtCore import Qt, QSize
from lunchinator import convert_string
from lunchinator.history_line_edit import HistoryLineEdit

class TableWidget(QWidget):
    PREFERRED_WIDTH = 400
    
    def __init__(self, parent, buttonText, triggeredEvent, sortedColumn = None, ascending = True, placeholderText = ""):
        super(TableWidget, self).__init__(parent)
        
        self.externalEvent = triggeredEvent
        
        # create HBox in VBox for each table
        # Create message table
        tableLayout = QVBoxLayout(self)
        tableBottomLayout = QHBoxLayout()
        
        self.table = QTreeView(self)
        self.table.setSortingEnabled(True)
        self.table.setHeaderHidden(False)
        self.table.setAlternatingRowColors(True)
        self.table.setIndentation(0)
        if sortedColumn != None:
            self.table.sortByColumn(sortedColumn, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
        tableLayout.addWidget(self.table)
        
        self.entry = HistoryLineEdit(self, placeholderText)
        tableBottomLayout.addWidget(self.entry)
        button = QPushButton(buttonText, self)
        tableBottomLayout.addWidget(button)
        tableLayout.addLayout(tableBottomLayout)
        
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
        
        
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    def foo(text):
        print text
    iface_gui_plugin.run_standalone(lambda window : TableWidget(window, "Enter", foo))