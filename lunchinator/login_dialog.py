from PyQt4.QtGui import QLineEdit, QDialog, QGridLayout, QLabel, QDialogButtonBox 
from lunchinator import convert_string

class LoginDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        
        self._username = None
        self._password = None

        formGridLayout = QGridLayout(self)
     
        self.editUserName = QLineEdit(self)
        self.editPassword = QLineEdit(self)
        self.editPassword.setEchoMode( QLineEdit.Password )
     
        labelUsername = QLabel(self)
        labelPassword = QLabel(self)
        labelUsername.setText("Username")
        labelUsername.setBuddy(self.editUserName)
        labelPassword.setText("Password")
        labelPassword.setBuddy(self.editPassword)
     
        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.Ok)
        buttons.addButton(QDialogButtonBox.Cancel)
     
        buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        buttons.button(QDialogButtonBox.Ok).clicked.connect(self.slotAcceptLogin)
     
        formGridLayout.addWidget(labelUsername, 0, 0)
        formGridLayout.addWidget(self.editUserName, 0, 1)
        formGridLayout.addWidget(labelPassword, 1, 0)
        formGridLayout.addWidget(self.editPassword, 1, 1)
        formGridLayout.addWidget(buttons, 2, 0, 1, 2)
     
        self.setLayout(formGridLayout)
        
    def slotAcceptLogin(self):
        self._username = convert_string(self.editUserName.text())
        self._password = convert_string(self.editUserName.text())
        self.setResult(QDialog.Accepted)
        self.setVisible(False)
        
    def getUsername(self):
        return self._username
    
    def getPassword(self):
        return self._password
