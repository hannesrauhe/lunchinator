from PyQt4.QtCore import QEvent, Qt
from PyQt4.QtGui import QLineEdit
class HistoryLineEdit(QLineEdit):
    def __init__(self, parent, placeholder):
        super(HistoryLineEdit, self).__init__(parent)
        self.history = []
        self.backups = {}
        self.index = 0 # 0 means newest line
        if hasattr(self, "setPlaceholderText"):
            self.setPlaceholderText(placeholder)
    
    def getText(self, index):
        if index == 0:
            # current line not in history
            return None
        return self.history[-index]
    
    def appendHistory(self, text):
        self.history.append(text)
    
    def handleHistory(self, newIndex):
        if self.index == 0 or self.getText(self.index) != self.text():
            # backup current line
            self.backups[self.index] = self.text()
        self.index = newIndex
        if self.index in self.backups:
            self.setText(self.backups[self.index])
        else:
            self.setText(self.getText(self.index))
        return True
    
    def event(self, event):
        if (event.type() == QEvent.KeyPress):
            if (event.key() == Qt.Key_Up):
                if len(self.history) > self.index:
                    return self.handleHistory(self.index + 1)
            elif(event.key() == Qt.Key_Down):
                if self.index > 0:
                    return self.handleHistory(self.index - 1)
            elif event.key() == Qt.Key_Return:
                if self.text().length() > 0:
                    if len(self.history) == 0 or self.getText(1) != self.text():
                        # only append to history if new text is different from last history entry
                        self.appendHistory(self.text())
                self.index = 0
                self.backups.clear()
        return super(HistoryLineEdit, self).event(event)