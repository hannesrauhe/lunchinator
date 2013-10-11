from PyQt4.QtGui import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy
from PyQt4.QtCore import Qt, QSize
from functools import partial
from lunchinator import convert_string

class TableWidget(QWidget):
    PREFERRED_WIDTH = 400
    
    def __init__(self, parent, buttonText, triggeredEvent, sortedColumn = None, ascending = True):
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
        
        self.entry = QLineEdit(self)
        tableBottomLayout.addWidget(self.entry)
        button = QPushButton(buttonText, self)
        tableBottomLayout.addWidget(button)
        tableLayout.addLayout(tableBottomLayout)
        
        self.entry.returnPressed.connect(self.eventTriggered)
        button.clicked.connect(self.eventTriggered)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def eventTriggered(self):
        text = convert_string(self.entry.text())
        self.externalEvent(text)
        self.entry.clear()
    
    def sizeHint(self):
        sizeHint = QWidget.sizeHint(self)
        return QSize(self.PREFERRED_WIDTH, sizeHint.height())
        
    def setModel(self, model):
        self.table.setModel(model)