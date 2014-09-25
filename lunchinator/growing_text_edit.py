from PyQt4.QtGui import QTextEdit, QSizePolicy, QWidget
from PyQt4.QtCore import QSize
from lunchinator.log.logging_slot import loggingSlot

class GrowingTextEdit(QTextEdit):
    def __init__(self, parent, heightMax = 1000):
        super(GrowingTextEdit, self).__init__(parent)  
        self.document().contentsChanged.connect(self.sizeChange)

        self.heightMin = 0
        self.heightMax = heightMax
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.sizeChange()

    def resizeEvent(self, event):
        self.sizeChange()
        return super(GrowingTextEdit, self).resizeEvent(event)

    def setDocHeight(self, height):
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)

    @loggingSlot()
    def sizeChange(self):
        docHeight = self.document().size().height()
        if self.heightMin <= docHeight <= self.heightMax:
            self.setDocHeight(docHeight + 2)
        elif docHeight < self.heightMin:
            self.setDocHeight(self.heightMin)
        else:
            self.setDocHeight(self.heightMax)
            
    def setVisible(self, *args, **kwargs):
        QTextEdit.setVisible(self, *args, **kwargs)
        self.sizeChange()
            
    def sizeHint(self):
        return QSize(QWidget.sizeHint(self).width(), self.minimumHeight())
    
