from PyQt4.QtCore import QEvent, Qt, pyqtSignal
from PyQt4.QtGui import QLineEdit, QKeyEvent
from lunchinator.growing_text_edit import GrowingTextEdit

class HistoryBase(object):
    def __init__(self, keyModifiers = Qt.NoModifier):
        super(HistoryBase, self).__init__()
        self.clearHistory()
        self.keyModifiers = keyModifiers
    
    def getText(self, index):
        if index == 0:
            # current line not in history
            return None
        return self.history[-index]
    
    def clearHistory(self):
        self.history = []
        self.backups = {}
        self.index = 0
    
    def appendHistory(self, text):
        if len(self.history) == 0 or text != self.history[-1]:
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
    
    def isQueryKey(self, event):
        return (event.key() == Qt.Key_Return and (int(event.modifiers()) & self.keyModifiers) == self.keyModifiers) or\
                event.key() == Qt.Key_Enter
    
    def event(self, event):
        if event.type() == QEvent.KeyPress:
            if (int(event.modifiers()) & self.keyModifiers) == self.keyModifiers:
                if (event.key() == Qt.Key_Up):
                    if len(self.history) > self.index:
                        return self.handleHistory(self.index + 1)
                elif(event.key() == Qt.Key_Down):
                    if self.index > 0:
                        return self.handleHistory(self.index - 1)
            if self.isQueryKey(event):
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
    returnPressed = pyqtSignal()
    
    def __init__(self, parent, triggerOnEnter=False):
        GrowingTextEdit.__init__(self, parent, 150)
        HistoryBase.__init__(self, Qt.ControlModifier)
        self._triggerOnEnter = triggerOnEnter
    
    def text(self):
        return self.toPlainText()
    
    def setText(self, text):
        self.setPlainText(text)
    
    def isQueryKey(self, event):
        if self._triggerOnEnter:
            return (event.key() == Qt.Key_Return and (int(event.modifiers()) & int(Qt.AltModifier | Qt.ShiftModifier)) == 0) or\
                    event.key() == Qt.Key_Enter
        else:
            return HistoryBase.isQueryKey(self, event)
    
    def event(self, event):
        retVal = HistoryBase.event(self, event)
        if event.type() == QEvent.KeyPress and self.isQueryKey(event):
            self.returnPressed.emit()
            return True
        if not retVal:
            if self._triggerOnEnter and \
               event.type() == QEvent.KeyPress and \
               event.key() == Qt.Key_Return and \
               ((int(event.modifiers()) & Qt.AltModifier) == Qt.AltModifier or \
                (int(event.modifiers()) & Qt.ShiftModifier) == Qt.ShiftModifier):
                event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, event.text(), event.isAutoRepeat(), event.count())
            return super(HistoryTextEdit, self).event(event)
        return True
