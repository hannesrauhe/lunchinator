from PyQt4.QtGui import QLineEdit
class PasswordEdit(QLineEdit):
    def __init__(self, hasValue, parent):
        super(PasswordEdit, self).__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        if hasValue:
            self.setText("*****")
        self.setModified(False)
        
        self._selectOnMousePress = True
        
    def focusInEvent(self, event):
        QLineEdit.focusInEvent(self, event)
        self._selectOnMousePress = True
    
    def mousePressEvent(self, event):
        QLineEdit.mousePressEvent(self, event)
        if self._selectOnMousePress:
            self.selectAll()
            self._selectOnMousePress = False

    def reset(self, hasValue):
        self.clear()
        if hasValue:
            self.setText("*****")
        self.setModified(False)