from PyQt4.QtGui import QWidget, QVBoxLayout
from PyQt4.QtCore import Qt
from PyQt4.Qt import QTextEdit
from lunchinator import get_notification_center
from lunchinator.log.logging_slot import loggingSlot

class ErrorConsole(QWidget):
    def __init__(self, parent):
        super(ErrorConsole, self).__init__(parent, Qt.Tool)
        self._initUI()
        get_notification_center().connectErrorOccurred(self._addError)
        
    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._errorLog = QTextEdit(self)
        self._errorLog.setReadOnly(True)
        layout.add(self._errorLog)
        
    @loggingSlot(int, object)
    def _addError(self, _level, message):
        self._errorLog.insertPlainText(message + '\n')
        if not self.isVisible():
            self.show()