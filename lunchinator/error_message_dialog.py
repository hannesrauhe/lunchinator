from PyQt4.QtGui import QDialog, QLabel, QVBoxLayout, QHBoxLayout,\
    QDialogButtonBox, QIcon
from PyQt4.QtCore import Qt
from lunchinator import get_settings

class ErrorMessageDialog(QDialog):
    def __init__(self, parent):
        super(ErrorMessageDialog, self).__init__(parent)
        
        self._errorPixmap = None
        self._warningPixmap = None
        try:
            from PyQt4.QtGui import QCommonStyle, QStyle
            style = QCommonStyle()
            self._errorPixmap = style.standardIcon(QStyle.SP_MessageBoxCritical).pixmap(14,14)
            if self._errorPixmap.isNull():
                self._errorPixmap = None
            self._warningPixmap = style.standardIcon(QStyle.SP_MessageBoxWarning).pixmap(14,14)
            if self._warningPixmap.isNull():
                self._warningPixmap = None
        except:
            pass
        
        if self._errorPixmap is None:
            self._errorPixmap = QIcon(get_settings().get_resource("images", "error.png")).pixmap(14,14)
        if self._warningPixmap is None:
            self._warningPixmap = QIcon(get_settings().get_resource("images", "warning.png")).pixmap(14,14)
            
        layout = QVBoxLayout(self)
        self._initInputUI(layout)
        self.__createBottomLayout(layout)
        self._initDone()
        
        size = self.sizeHint()
        self.setMaximumHeight(size.height())

    def __createBottomLayout(self, layout):
        errorLayout = QHBoxLayout()
        errorLayout.setContentsMargins(0, 0, 0, 0)
        
        self._errorIconLabel = QLabel(self)
        self._errorIconLabel.setAlignment(Qt.AlignCenter)
        self._errorIconLabel.setVisible(False)
        errorLayout.addWidget(self._errorIconLabel, 0, Qt.AlignLeft)
        
        self._errorLabel = QLabel(self)
        self._errorLabel.setVisible(False)
        errorLayout.addWidget(self._errorLabel, 1, Qt.AlignLeft)
        layout.addLayout(errorLayout)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttonBox.accepted.connect(self._checkOK)
        buttonBox.rejected.connect(self.reject)
        
        layout.addWidget(buttonBox, 0, Qt.AlignRight)
        
    def _error(self, msg, warning=False):
        self._errorIconLabel.setPixmap(self._warningPixmap if warning else self._errorPixmap)
        self._errorIconLabel.setVisible(True)
        self._errorLabel.setText(msg)
        self._errorLabel.setVisible(True)

    ############## To be implemented in subclass ############
            
    def _initInputUI(self, layout):
        raise NotImplementedError()
                
    def _checkOK(self):
        raise NotImplementedError()

    ############## Optional #################
    def _initDone(self):
        pass