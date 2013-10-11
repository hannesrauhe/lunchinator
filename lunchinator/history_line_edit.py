from PyQt4.QtCore import QEvent, Qt, Signal
from PyQt4.QtGui import QLineEdit
from lunchinator.growing_text_edit import GrowingTextEdit

class HistoryBase(object):
    def __init__(self, keyModifiers = Qt.NoModifier):
        super(HistoryBase, self).__init__()
        self.history = []
        self.backups = {}
        self.index = 0 # 0 means newest line
        self.keyModifiers = keyModifiers
    
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
        if event.type() == QEvent.KeyPress and event.modifiers() == self.keyModifiers:
            if (event.key() == Qt.Key_Up):
                if len(self.history) > self.index:
                    return self.handleHistory(self.index + 1)
            elif(event.key() == Qt.Key_Down):
                if self.index > 0:
                    return self.handleHistory(self.index - 1)
            elif event.key() == Qt.Key_Return:
                if len(self.text()) > 0:
                    if len(self.history) == 0 or self.getText(1) != self.text():
                        # only append to history if new text is different from last history entry
                        self.appendHistory(self.text())
                self.index = 0
                self.backups.clear()
        return False

class HistoryLineEdit(QLineEdit, HistoryBase):
    def __init__(self, parent, placeholder):
        QLineEdit.__init__(self, parent)
        HistoryBase.__init__(self)
        if hasattr(self, "setPlaceholderText"):
            self.setPlaceholderText(placeholder)
    
    def event(self, event):
        if not HistoryBase.event(self, event):
            return super(HistoryLineEdit, self).event(event)
        return True

class HistoryTextEdit(GrowingTextEdit, HistoryBase):
    returnPressed = Signal()
    
    def __init__(self, parent):
        GrowingTextEdit.__init__(self, parent, 150)
        HistoryBase.__init__(self, Qt.ControlModifier)
    
    def text(self):
        return self.toPlainText()
    
    def setText(self, text):
        self.setPlainText(text)
    
    def event(self, event):
        retVal = HistoryBase.event(self, event)
        if (event.type() == QEvent.KeyPress):
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
                self.returnPressed.emit()
        if not retVal:
            return super(HistoryTextEdit, self).event(event)
        return True
