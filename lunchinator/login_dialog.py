from PyQt4.QtGui import QLineEdit, QDialog, QGridLayout, QLabel, QDialogButtonBox, QSizePolicy
from PyQt4.QtCore import Qt 
from lunchinator import convert_string

class LoginDialog(QDialog):
    def __init__(self, parent, description = "Please enter your login information:", loginText = "Login:", passwordText = "Password:"):
        QDialog.__init__(self, parent)
        
        self._username = None
        self._password = None
        
        formGridLayout = QGridLayout(self)
     
        descLabel = QLabel(description, self)
        descLabel.setWordWrap(True)
        descLabel.setContentsMargins(0,0,0,5)
     
        self.editUserName = QLineEdit(self)
        self.editPassword = QLineEdit(self)
        self.editPassword.setEchoMode( QLineEdit.Password )
     
        labelUsername = QLabel(self)
        labelPassword = QLabel(self)
        labelUsername.setText(loginText)
        labelUsername.setBuddy(self.editUserName)
        labelPassword.setText(passwordText)
        labelPassword.setBuddy(self.editPassword)
     
        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.Ok)
        buttons.addButton(QDialogButtonBox.Cancel)
     
        buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        buttons.button(QDialogButtonBox.Ok).clicked.connect(self.slotAcceptLogin)
     
        formGridLayout.addWidget(descLabel, 0, 0, 1, 2)
        formGridLayout.addWidget(labelUsername, 1, 0, 1, 1, Qt.AlignRight)
        formGridLayout.addWidget(self.editUserName, 1, 1)
        formGridLayout.addWidget(labelPassword, 2, 0, 1, 1, Qt.AlignRight)
        formGridLayout.addWidget(self.editPassword, 2, 1)
        formGridLayout.addWidget(buttons, 3, 0, 1, 2, Qt.AlignBottom)
        formGridLayout.setRowStretch(0, 0)
        formGridLayout.setRowStretch(1, 0)
        formGridLayout.setRowStretch(2, 0)
        formGridLayout.setRowStretch(3, 1)
        
        self.setMaximumHeight(self.sizeHint().height())
        self.setMinimumHeight(self.sizeHint().height())
        #self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        
    def slotAcceptLogin(self):
        self._username = convert_string(self.editUserName.text())
        self._password = convert_string(self.editPassword.text())
        self.setResult(QDialog.Accepted)
        self.setVisible(False)
        
    def getUsername(self):
        return self._username
    
    def getPassword(self):
        return self._password
