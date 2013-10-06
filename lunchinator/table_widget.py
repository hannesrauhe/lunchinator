from PyQt4.QtGui import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt4.QtCore import Qt
from functools import partial

class TableWidget(QWidget):
    def __init__(self, parent, buttonText, triggeredEvent, sortedColumn = None, ascending = True):
        super(TableWidget, self).__init__(parent)
        
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
        
        entry = QLineEdit(self)
        tableBottomLayout.addWidget(entry)
        button = QPushButton(buttonText, self)
        tableBottomLayout.addWidget(button)
        tableLayout.addLayout(tableBottomLayout)
        
        entry.returnPressed.connect(partial(triggeredEvent, entry))
        button.clicked.connect(partial(triggeredEvent, entry))
        
    def setModel(self, model):
        self.table.setModel(model)