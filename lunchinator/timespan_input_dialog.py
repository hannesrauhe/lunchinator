from PyQt4.QtGui import QTimeEdit, QLabel, QHBoxLayout, QWidget
from PyQt4.Qt import Qt
from PyQt4.QtCore import QTime
from lunchinator.lunch_settings import lunch_settings
from lunchinator.utilities import getTimeDifference
from lunchinator.gui_elements import ErrorMessageDialog
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.log import getCoreLogger

class TimespanInputDialog(ErrorMessageDialog):
    def __init__(self, parent, title, message, initialBegin, initialEnd, checkBeforeNow=True):
        self._checkBeforeNow = checkBeforeNow
        self._title = title
        self._message = message
        self._initialBegin = initialBegin
        self._initialEnd = initialEnd
        
        super(TimespanInputDialog, self).__init__(parent)
        
    def _initInputUI(self, layout):
        self.setWindowTitle(self._title)
        messageLabel = QLabel(self._message, self)
        messageLabel.setWordWrap(True)
        layout.addWidget(messageLabel)

        inputWidget = QWidget(self)
        inputLayout = QHBoxLayout(inputWidget)
        inputLayout.setContentsMargins(0, 0, 0, 0)
                
        if type(self._initialBegin) != QTime:
            initialBegin = QTime.fromString(self._initialBegin, lunch_settings.LUNCH_TIME_FORMAT_QT)
        if type(self._initialEnd) != QTime:
            initialEnd = QTime.fromString(self._initialEnd, lunch_settings.LUNCH_TIME_FORMAT_QT)
                
        inputLayout.addWidget(QLabel("From", self))
        self.beginEdit = QTimeEdit(self)
        self.beginEdit.setDisplayFormat("HH:mm")
        self.beginEdit.setTime(initialBegin)
        inputLayout.addWidget(self.beginEdit)
        
        inputLayout.addWidget(QLabel("to", self))
        self.endEdit = QTimeEdit(self)
        self.endEdit.setDisplayFormat("HH:mm")
        self.endEdit.setTime(initialEnd)
        inputLayout.addWidget(self.endEdit)
        
        layout.addWidget(inputWidget, 0, Qt.AlignLeft)
        
    @loggingSlot()
    def _checkOK(self):
        if self.getEndTime() < self.getBeginTime():
            self._error(u"End time is before begin time.")
        elif self._checkBeforeNow and \
             getTimeDifference(self.getBeginTimeString(), self.getEndTimeString(), getCoreLogger()) == 0:
            self._error(u"The time span is already over.")
        else:
            self.accept()
        
    def getBeginTime(self):
        return self.beginEdit.time().toPyTime()
    def getBeginTimeString(self):
        return self.beginEdit.time().toPyTime().strftime(lunch_settings.LUNCH_TIME_FORMAT)
    
    def getEndTime(self):
        return self.endEdit.time().toPyTime()
    def getEndTimeString(self):
        return self.endEdit.time().toPyTime().strftime(lunch_settings.LUNCH_TIME_FORMAT)

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = TimespanInputDialog(None, "Test", "This is a test.", "12:15", "12:45")
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()

