from PyQt4.QtGui import QDialog, QLabel, QHBoxLayout,\
    QWidget, QPushButton, QStyle, QLineEdit, QCheckBox,\
    QFileDialog
from PyQt4.QtCore import Qt
from lunchinator import convert_string
from lunchinator.git import GitHandler
import os
from lunchinator.error_message_dialog import ErrorMessageDialog

class AddRepoDialog(ErrorMessageDialog):
    def __init__(self, parent):
        super(AddRepoDialog, self).__init__(parent)
        
        self._path = None
        self._active = True
        self._autoUpdate = False
        self._canAutoUpdate = False
        
    def _initInputUI(self, layout):
        style = None
        try:
            from PyQt4.QtGui import QCommonStyle
            style = QCommonStyle()
        except:
            pass
        
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
        if style != None:
            browseIcon = style.standardIcon(QStyle.SP_DirOpenIcon)
        else:
            browseIcon = None
        
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
        
    def _checkOK(self):
        if not os.path.isdir(self.getPath()):
            self._error("The given path does not exist or is not a directory.")
        else:
            self.accept()

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = AddRepoDialog(None)
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()

