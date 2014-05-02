from PyQt4.QtGui import QDialog, QLabel, QVBoxLayout, QHBoxLayout,\
    QWidget, QPushButton, QStyle, QCommonStyle, QLineEdit, QCheckBox,\
    QFileDialog
from PyQt4.Qt import Qt
from lunchinator import convert_string
from lunchinator.git import GitHandler
import os

class AddRepoDialog(QDialog):
    def __init__(self, parent):
        super(AddRepoDialog, self).__init__(parent)
        
        self._path = None
        self._active = True
        self._autoUpdate = False
        self._canAutoUpdate = False
        
        layout = QVBoxLayout(self)
        
        style = QCommonStyle()
        
        self.setWindowTitle(u"Add Plugin Repository")

        inputWidget = QWidget(self)
        inputLayout = QHBoxLayout(inputWidget)
        inputLayout.setContentsMargins(0, 0, 0, 0)
        
        inputLayout.addWidget(QLabel("Path:", self))
        self.pathEdit = QLineEdit(self)
        self.pathEdit.returnPressed.connect(self._checkPath)
        inputLayout.addWidget(self.pathEdit, 1)
        
        browseButton = QPushButton(self)
        browseButton.setAutoDefault(False)
        browseIcon = style.standardIcon(QStyle.SP_DirOpenIcon)
        if browseIcon:
            browseButton.setIcon(browseIcon)
        else:
            browseButton.setText("Browse...")
        browseButton.clicked.connect(self._browse)
        inputLayout.addWidget(browseButton, 0, Qt.AlignHCenter)
        
        layout.addWidget(inputWidget, 0)
        
        propertiesLayout = QHBoxLayout()
        propertiesLayout.setContentsMargins(0, 0, 0, 0)
        
        activeCheckBox = QCheckBox("Active", self)
        activeCheckBox.stateChanged.connect(self._activeChanged)
        activeCheckBox.setChecked(True)
        propertiesLayout.addWidget(activeCheckBox)
        
        self.autoUpdateCheckBox = QCheckBox("Auto Update", self)
        self.autoUpdateCheckBox.setEnabled(False)
        self.autoUpdateCheckBox.stateChanged.connect(self._autoUpdateChanged)
        propertiesLayout.addWidget(self.autoUpdateCheckBox, 1, Qt.AlignLeft)
        
        layout.addLayout(propertiesLayout)
                
        errorLayout = QHBoxLayout()
        errorLayout.setContentsMargins(0, 0, 0, 0)
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
        cancelButton.setAutoDefault(False)
        buttonLayout.addWidget(cancelButton)
        
        okButton = QPushButton("OK", self)
        okButton.clicked.connect(self.checkOK)
        okButton.setAutoDefault(False)
        buttonLayout.addWidget(okButton)
        
        layout.addWidget(buttonWidget, 0, Qt.AlignRight)
        
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        self.setMinimumWidth(300)
        
    def _activeChanged(self, newState):
        self._active = newState == Qt.Checked
        
    def _autoUpdateChanged(self, newState):
        self._autoUpdate = newState == Qt.Checked
        
    def _browse(self):
        fd = QFileDialog(self)
        fd.setOptions(QFileDialog.ShowDirsOnly)
        fd.setFileMode(QFileDialog.Directory)
        fd.exec_()
        if fd.result() == QDialog.Accepted:
            path = fd.selectedFiles()[0]
            self._setPath(path)
        
    def _checkPath(self):
        self._canAutoUpdate = GitHandler.hasGit(self.getPath())
        
        self.autoUpdateCheckBox.setEnabled(self._canAutoUpdate)
        if not self._canAutoUpdate:
            self.autoUpdateCheckBox.setChecked(False)
        
    def _error(self, msg):
        self._errorIcon.setVisible(True)
        self._errorLabel.setText(msg)
        self._errorLabel.setVisible(True)
    
    def _setPath(self, path):
        self._path = convert_string(path)
        self.pathEdit.setText(path)
        self._checkPath()
    
    def getPath(self):
        if convert_string(self.pathEdit.text()) != self._path:
            self._setPath(convert_string(self.pathEdit.text()))
        return self._path
    
    def isRepositoryActive(self):
        return self._active
    
    def isAutoUpdateEnabled(self):
        return self._autoUpdate
    
    def canAutoUpdate(self):
        return self._canAutoUpdate
    
    def _setAutoUpdate(self, autoUpdate):
        self._autoUpdate = autoUpdate
        self.autoUpdateCheckBox.setChecked(autoUpdate)
        
    def checkOK(self):
        if not os.path.isdir(self.getPath()):
            self._error("The given path does not exist or is not a directory.")
        else:
            self.accept()

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = AddRepoDialog(None)
    
    window.show()
    window.activateWindow()
    window.raise_()
    
    app.exec_()

