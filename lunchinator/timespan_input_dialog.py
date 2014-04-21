from PyQt4.QtGui import QDialog, QTimeEdit, QLabel, QVBoxLayout, QHBoxLayout,\
    QWidget, QPushButton, QStyle, QCommonStyle
from PyQt4.Qt import Qt
from PyQt4.QtCore import QTime
from lunchinator.lunch_settings import lunch_settings
from lunchinator.utilities import getTimeDifference

class TimespanInputDialog(QDialog):
    def __init__(self, parent, title, message, initialBegin, initialEnd, checkBeforeNow=True):
        super(TimespanInputDialog, self).__init__(parent)
        
        self._checkBeforeNow = checkBeforeNow
        
        layout = QVBoxLayout(self)
        
        self.setWindowTitle(title)
        messageLabel = QLabel(message, self)
        messageLabel.setWordWrap(True)
        layout.addWidget(messageLabel)

        inputWidget = QWidget(self)
        inputLayout = QHBoxLayout(inputWidget)
        inputLayout.setContentsMargins(0, 0, 0, 0)
                
        if type(initialBegin) != QTime:
            initialBegin = QTime.fromString(initialBegin, lunch_settings.LUNCH_TIME_FORMAT_QT)
        if type(initialEnd) != QTime:
            initialEnd = QTime.fromString(initialEnd, lunch_settings.LUNCH_TIME_FORMAT_QT)
                
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
        
        errorLayout = QHBoxLayout()
        errorLayout.setContentsMargins(0, 0, 0, 0)
        style = QCommonStyle()
        self._errorIcon = QLabel(self)
        self._errorIcon.setPixmap(style.standardIcon(QStyle.SP_MessageBoxWarning).pixmap(12,12))
        self._errorIcon.setAlignment(Qt.AlignTop)
        self._errorIcon.setVisible(False)
        errorLayout.addWidget(self._errorIcon, 0, Qt.AlignLeft)
        
        self._errorLabel = QLabel(self)
        self._errorLabel.setVisible(False)
        errorLayout.addWidget(self._errorLabel, 1, Qt.AlignLeft)
        layout.addLayout(errorLayout)
        
        buttonWidget = QWidget(self)
        buttonLayout = QHBoxLayout(buttonWidget)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        
        cancelButton = QPushButton("Cancel", self)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(cancelButton)
        
        okButton = QPushButton("OK", self)
        okButton.clicked.connect(self.checkOK)
        okButton.setDefault(True)
        buttonLayout.addWidget(okButton)
        
        layout.addWidget(buttonWidget, 0, Qt.AlignRight)
        
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        
    def _error(self, msg):
        self._errorIcon.setVisible(True)
        self._errorLabel.setText(msg)
        self._errorLabel.setVisible(True)
        
    def checkOK(self):
        if self.getEndTime() < self.getBeginTime():
            self._error(u"End time is before begin time.")
        elif self._checkBeforeNow and \
             getTimeDifference(self.getBeginTimeString(), self.getEndTimeString()) == 0:
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
    
    window.show()
    window.activateWindow()
    window.raise_()
    
    app.exec_()

