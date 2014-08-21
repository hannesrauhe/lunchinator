from PyQt4.QtGui import QDialog, QLabel, QHBoxLayout,\
    QWidget, QPushButton, QStyle, QLineEdit, QCheckBox,\
    QFileDialog, QVBoxLayout, QTabWidget
from PyQt4.Qt import Qt
from lunchinator import convert_string, get_settings
from lunchinator.git import GitHandler
import os
from lunchinator.error_message_dialog import ErrorMessageDialog
from lunchinator.callables import AsyncCall
from lunchinator.utilities import getUniquePath

class AddRepoDialog(ErrorMessageDialog):
    _WORKING_COPY = 0
    _CLONE_URL = 1
    
    def __init__(self, parent):
        super(AddRepoDialog, self).__init__(parent)
        self._canAutoUpdate = False
        self._closeable = True
        self._path = None
        
    def _createPathPage(self):
        try:
            from PyQt4.QtGui import QCommonStyle
            style = QCommonStyle()
        except:
            style = None
        
        w = QWidget(self)
        layout = QVBoxLayout(w)
        
        inputWidget = QWidget(self)
        inputLayout = QHBoxLayout(inputWidget)
        inputLayout.setContentsMargins(0, 0, 0, 0)
        
        inputLayout.addWidget(QLabel("Path:", self))
        self._pathEdit = QLineEdit(self)
        if hasattr(self._pathEdit, "setPlaceholderText"):
            self._pathEdit.setPlaceholderText(u"Directory Path")
        inputLayout.addWidget(self._pathEdit, 1)
        
        browseButton = QPushButton(self)
        browseButton.setAutoDefault(False)
        if style != None:
            browseIcon = style.standardIcon(QStyle.SP_DirOpenIcon)
        else:
            browseIcon = None
        
        if browseIcon and not browseIcon.isNull():
            browseButton.setIcon(browseIcon)
        else:
            browseButton.setText("Browse...")
        browseButton.clicked.connect(self._browse)
        inputLayout.addWidget(browseButton, 0, Qt.AlignHCenter)
        
        layout.addWidget(inputWidget, 0)        
        return w, layout
    
    def _createURLPage(self):
        w = QWidget(self)
        layout = QVBoxLayout(w)
        
        inputWidget = QWidget(self)
        inputLayout = QHBoxLayout(inputWidget)
        inputLayout.setContentsMargins(0, 0, 0, 0)
        
        inputLayout.addWidget(QLabel("URL:", self))
        self._urlEdit = QLineEdit(self)
        if hasattr(self._urlEdit, "setPlaceholderText"):
            self._urlEdit.setPlaceholderText(u"Git URL (HTTPS/SSH)")
        inputLayout.addWidget(self._urlEdit, 1)
        
        layout.addWidget(inputWidget, 0)        
        return w, layout
        
    def _addPropertyWidgets(self, layout, autoUpdateEnabled):
        propertiesLayout = QHBoxLayout()
        propertiesLayout.setContentsMargins(0, 0, 0, 0)
        
        activeCheckBox = QCheckBox("Active", self)
        activeCheckBox.setChecked(True)
        propertiesLayout.addWidget(activeCheckBox)
        self._activeBoxes.append(activeCheckBox)
        
        autoUpdateCheckBox = QCheckBox("Auto Update", self)
        autoUpdateCheckBox.setEnabled(autoUpdateEnabled)
        propertiesLayout.addWidget(autoUpdateCheckBox, 1, Qt.AlignLeft)
        self._autoUpdateBoxes.append(autoUpdateCheckBox)
        
        layout.addLayout(propertiesLayout)
        
    def _initInputUI(self, dialogLayout):
        self.setWindowTitle(u"Add Plugin Repository")

        self._tabs = QTabWidget(self)
        
        self._activeBoxes = []
        self._autoUpdateBoxes = []

        w, layout = self._createPathPage()
        self._addPropertyWidgets(layout, False)
        self._tabs.addTab(w, "Working Copy")
        
        w, layout = self._createURLPage()
        self._addPropertyWidgets(layout, True)
        self._tabs.addTab(w, "Clone URL")
        
        dialogLayout.addWidget(self._tabs)
                
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
        
        box = self._autoUpdateBoxes[self._WORKING_COPY]
        if not self._canAutoUpdate:
            box.setChecked(False)
        if box.isEnabled() != self._canAutoUpdate: 
            box.setEnabled(self._canAutoUpdate)
            return True
        return False
            
    def _setPath(self, path):
        self._pathEdit.setText(path)
        self._checkPath()
    
    def getPath(self):
        if self._path is not None:
            return self._path
        return convert_string(self._pathEdit.text())
    
    def isRepositoryActive(self):
        return self._activeBoxes[self._tabs.currentIndex()].checkState() == Qt.Checked
    
    def isAutoUpdateEnabled(self):
        return self._autoUpdateBoxes[self._tabs.currentIndex()].checkState() == Qt.Checked
    
    def canAutoUpdate(self):
        return self._tabs.currentIndex() == self._CLONE_URL or self._canAutoUpdate
    
    def _setWorking(self, w):
        self._closeable = not w
        self._tabs.setEnabled(not w)
        self._setButtonsEnabled(not w)
    
    def _checkOK(self):
        if self._tabs.currentIndex() == self._WORKING_COPY:
            if not os.path.isdir(self.getPath()):
                self._error("The given path does not exist or is not a directory.")
            elif not self._checkPath():
                # no change to properties widget -> accept
                self._path = self.getPath()
                self.accept()
        else:
            self._info(u"Cloning repository...")
            self._setWorking(True)
            url = convert_string(self._urlEdit.text())
            AsyncCall(self, self._checkAndClone, self._cloneSuccess, self._cloneError)(url)

    def closeEvent(self, event):
        if self._closeable:
            event.accept()
        else:
            event.ignore()

    def _checkAndClone(self, url):
        if not GitHandler.isGitURL(url):
            raise ValueError(u"The given URL does not exist or is no Git repository.")

        targetDir = get_settings().get_config(GitHandler.extractRepositoryNameFromURL(url))
        targetDir = getUniquePath(targetDir)
        GitHandler.clone(url, targetDir)
        return targetDir
        
    def _cloneSuccess(self, path):
        self._setWorking(False)
        self.setResult(self.Accepted)
        self._path = path
        self.close()
        
    def _cloneError(self, msg):
        self._setWorking(False)
        self._error(msg)
        
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = AddRepoDialog(None)
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()
    
    print "path:", window.getPath()

