from PyQt4.QtGui import QDialog, QTimeEdit, QLabel, QVBoxLayout, QHBoxLayout,\
    QWidget, QPushButton
from PyQt4.Qt import Qt
from PyQt4.QtCore import QTime
from lunchinator.lunch_settings import lunch_settings

class TimespanInputDialog(QDialog):
    def __init__(self, parent, title, message, initialBegin, initialEnd):
        super(TimespanInputDialog, self).__init__(parent)
        
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
        
        buttonWidget = QWidget(self)
        buttonLayout = QHBoxLayout(buttonWidget)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        
        cancelButton = QPushButton("Cancel", self)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(cancelButton)
        
        okButton = QPushButton("OK", self)
        okButton.clicked.connect(self.accept)
        okButton.setDefault(True)
        buttonLayout.addWidget(okButton)
        
        layout.addWidget(buttonWidget, 0, Qt.AlignRight)
        
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        
    def getBeginTime(self):
        return self.beginEdit.time().getPyTime()
    def getBeginTimeString(self):
        return self.beginEdit.time().getPyTime().strftime(lunch_settings.LUNCH_TIME_FORMAT)
    
    def getEndTime(self):
        return self.endEdit.time().getPyTime()
    def getEndTimeString(self):
        return self.endEdit.time().getPyTime().strftime(lunch_settings.LUNCH_TIME_FORMAT)
