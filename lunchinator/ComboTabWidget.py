from PyQt4.QtGui import QWidget, QVBoxLayout, QStackedWidget, QComboBox, QGroupBox
from PyQt4.QtCore import Qt

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
        
    def removeTab(self, index=-1):
        if index<0:
            index = self.switchCombo.currentIndex()
        self.switchCombo.removeItem(index)
        self.pageArea.removeWidget(index)
        
    def updateTab(self, w, tabText, index=-1):
        if index<0:
            index = self.switchCombo.currentIndex()
        self.removeTab(index)
        
        self.switchCombo.insertItem(index, tabText)
        self.pageArea.insertItem(index, w)
        
    def setCurrentIndex(self, index):
        self.switchCombo.setCurrentIndex(index)
        
    def currentIndex(self):
        return self.switchCombo.currentIndex()
    
    def count(self):
        return self.switchCombo.count()