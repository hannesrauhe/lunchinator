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
    
    def insertTab(self, pos, w, tabText):
        self.pageArea.insertWidget(pos, w)
        self.switchCombo.insertItem(pos, tabText)
        
    def removeTab(self, index=-1):
        if index < 0:
            index = self.currentIndex()
        
        w = self.pageArea.widget(index)
        
        self.pageArea.removeWidget(w)
        self.switchCombo.removeItem(index)
        
    def updateTab(self, w, tabText, index=-1):
        if index < 0:
            index = self.switchCombo.currentIndex()
        
        self.removeTab(index)
        self.insertTab(index, w, tabText)
        self.setCurrentIndex(index)
        
    def setCurrentIndex(self, index):
        self.switchCombo.setCurrentIndex(index)
        
    def currentIndex(self):
        return self.switchCombo.currentIndex()
    
    def count(self):
        return self.switchCombo.count()
