from PySide.QtGui import QWidget, QVBoxLayout, QStackedWidget, QComboBox, QGroupBox
from PySide.QtCore import Qt

class ComboTabWidget(QWidget):
    def __init__(self, parent):
        super(ComboTabWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        self.switchCombo = QComboBox(self)
        layout.addWidget(self.switchCombo, 0, Qt.AlignCenter)
        
        groupBox = QGroupBox(self)
        groupBoxLayout = QVBoxLayout(groupBox)
        groupBoxLayout.setSpacing(0)
        
        self.pageArea = QStackedWidget(groupBox)
        groupBoxLayout.addWidget(self.pageArea)
        
        layout.addWidget(groupBox, 1)
        
        self.switchCombo.currentIndexChanged.connect(self.pageArea.setCurrentIndex)
        
    def setTabPosition(self, tabPos):
        pass
        
    def addTab(self, w, tabText):
        self.pageArea.addWidget(w)
        self.switchCombo.addItem(tabText)
        
    def setCurrentIndex(self, index):
        self.switchCombo.setCurrentIndex(index)
        
    def currentIndex(self):
        return self.switchCombo.currentIndex()
    
    def count(self):
        return self.switchCombo.count()