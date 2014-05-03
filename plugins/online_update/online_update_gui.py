from PyQt4.QtGui import QWidget, QTextCursor, QTextListFormat,\
                        QVBoxLayout, QLabel, QSizePolicy, QPushButton, \
                        QTextEdit, QProgressBar, QGroupBox
from PyQt4.QtCore import pyqtSignal

class OnlineUpdateGUI(QWidget):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    
    checkForAppUpdate = pyqtSignal()
    checkForRepoUpdates = pyqtSignal()
    installUpdates = pyqtSignal()
    
    def __init__(self, installedVersion, parent):
        super(OnlineUpdateGUI, self).__init__(parent)
        
        self._appCheckWasEnabled = False
        self._installWasEnabled = False
        
        layout = QVBoxLayout(self)
        layout.addWidget(self._createAppUpdateWidget(installedVersion))
        layout.addWidget(self._createRepoUpdateWidget())
        
        self._installUpdatesButton = QPushButton("Install Update(s) and Restart", self)
        self._installUpdatesButton.clicked.connect(self.installUpdates)
        self._installUpdatesButton.setEnabled(False)
        layout.addWidget(self._installUpdatesButton)
        self._spacing = QWidget(self)
        layout.addWidget(self._spacing, 1)
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        
    def _createAppUpdateWidget(self, installedVersion):
        widget = QGroupBox("Application", self)
        
        layout = QVBoxLayout(widget)
        versionLabel = QLabel("Installed Version: " + installedVersion)
        layout.addWidget(versionLabel, 0)
        
        self._appStatusLabel = QLabel(widget)
        self._appStatusLabel.setWordWrap(True)
        layout.addWidget(self._appStatusLabel, 0)
        
        self._progressBar = QProgressBar(widget)
        self._progressBar.setVisible(False)
        layout.addWidget(self._progressBar, 0)
        
        self._appCheckButton = QPushButton("Check for Update", widget)
        self._appCheckButton.clicked.connect(self.checkForAppUpdate)
        
        layout.addWidget(self._appCheckButton, 0)
        
        self._appChangeLog = QTextEdit(self)
        self._appChangeLog.setReadOnly(True)
        self._appChangeLog.setVisible(False)
        layout.addWidget(self._appChangeLog, 1)
        
        return widget
        
    def _createRepoUpdateWidget(self):
        widget = QGroupBox("Plugin Repositories", self)
        layout = QVBoxLayout(widget)
        
        self._repoStatusLabel = QLabel(widget)
        layout.addWidget(self._repoStatusLabel)
        
        self._repoCheckButton = QPushButton("Check for Updates", widget)
        self._repoCheckButton.clicked.connect(self.checkForRepoUpdates)
        layout.addWidget(self._repoCheckButton)
        
        return widget
        
    def setChangelogVisible(self, v):
        self._appChangeLog.setVisible(v)
        self._spacing.setVisible(not v)
        
    def setProgress(self, prog):
        self._progressBar.setValue(prog)
        
    def setProgressIndeterminate(self, indeterminate):
        self._progressBar.setMaximum(0 if indeterminate else 100)
        
    def setCheckAppUpdateButtonText(self, text=None):
        if not text:
            text = "Check for Update"
        self._appCheckButton.setText(text)
        
    def setInteractive(self, interactive):
        if interactive:
            self._appCheckButton.setEnabled(self._appCheckWasEnabled)
            self._installUpdatesButton.setEnabled(self._installWasEnabled)
        else:
            self._appCheckWasEnabled = self._appCheckButton.isEnabled()
            self._installWasEnabled = self._installUpdatesButton.isEnabled()
            
            self._appCheckButton.setEnabled(False)
            self._installUpdatesButton.setEnabled(False)

    def setCanCheckForAppUpdate(self, can):
        self._appCheckButton.setEnabled(can)
        
    def setCanCheckForRepoUpdate(self, can):
        self._repoCheckButton.setEnabled(can)

    def appInstallReady(self):
        self._installUpdatesButton.setEnabled(True)
        
    def setRepoUpdatesAvailable(self, avail):
        self._installUpdatesButton.setEnabled(avail)
        
    def setRepoStatus(self, status):
        self._repoStatusLabel.setText(status)
        
    def setAppStatus(self, status, progress=False):
        self._progressBar.setVisible(progress)
        self._appStatusLabel.setText(status)
            
    def setAppStatusToolTip(self, text):
        self._appStatusLabel.setToolTip(text)
        
    def setAppChangeLog(self, log):
        self._appChangeLog.clear()
        document = self._appChangeLog.document()
        document.setIndentWidth(20)
        cursor = QTextCursor(document)
        
        cursor.insertText("Changes:\n")
    
        listFormat = QTextListFormat()
        listFormat.setStyle(QTextListFormat.ListDisc)
        cursor.insertList(listFormat)
    
        cursor.insertText("\n".join(log))
        self.setChangelogVisible(True)
    