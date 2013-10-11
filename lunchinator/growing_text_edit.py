from PySide.QtGui import QTextEdit, QSizePolicy, QWidget
from PySide.QtCore import QSize

class GrowingTextEdit(QTextEdit):
    def __init__(self, parent, heightMax = 1000):
        super(GrowingTextEdit, self).__init__(parent)  
        self.document().contentsChanged.connect(self.sizeChange)

        self.heightMin = 0
        self.heightMax = heightMax
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.sizeChange()

    def resizeEvent(self, *args, **kwargs):
        self.sizeChange()
        return QTextEdit.resizeEvent(self, *args, **kwargs)

    def sizeChange(self):
        docHeight = self.document().size().height()
        if self.heightMin <= docHeight <= self.heightMax:
            self.setMinimumHeight(docHeight + 2)
            self.setMaximumHeight(docHeight + 2)
            
    def setVisible(self, *args, **kwargs):
        QTextEdit.setVisible(self, *args, **kwargs)
        self.sizeChange()
            
    def sizeHint(self):
        return QSize(QWidget.sizeHint(self).width(), self.minimumHeight())
    