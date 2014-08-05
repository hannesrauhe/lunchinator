from PyQt4.QtGui import QDialog, QLabel, QVBoxLayout, QHBoxLayout,\
    QLineEdit, QFormLayout, QDialogButtonBox, QIcon
from PyQt4.Qt import Qt
from lunchinator import get_peers, convert_string, get_settings
import re

class RemotePicturesDialog(QDialog):
    _urlRegex = None
    
    def __init__(self, parent, peerID, peerInfo):
        super(RemotePicturesDialog, self).__init__(parent)
        
        if get_peers() is not None:
            peerName = get_peers().getDisplayedPeerName(pID=peerID)
        else:
            peerName = "<peer name here>"

        self._initUI(peerName)
        
        if peerInfo is None or not u"RP_v" in peerInfo:
            self._error("%s might not be able to receive remote pictures." % peerName, True)
        
    def _initUI(self, peerName):
        layout = QVBoxLayout(self)
                
        self.setWindowTitle(u"Send Remote Picture")
        messageLabel = QLabel(u"Send a remote picture to %s" % peerName, self)
        layout.addWidget(messageLabel)
        layout.addSpacing(5)

        formLayout = QFormLayout()
        formLayout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        formLayout.setContentsMargins(0, 0, 0, 0)
        self.urlInput = QLineEdit(self)
        if hasattr(self.urlInput, "setPlaceholderText"):
            self.urlInput.setPlaceholderText("Image URL")
        formLayout.addRow(u"Image URL:", self.urlInput)
        
        self.descInput = QLineEdit(self)
        if hasattr(self.descInput, "setPlaceholderText"):
            self.descInput.setPlaceholderText("Description text")
        formLayout.addRow(u"Description:", self.descInput)
        
        self.catInput = QLineEdit(self)
        if hasattr(self.catInput, "setPlaceholderText"):
            self.catInput.setPlaceholderText("Category (empty = uncategorized)")
        formLayout.addRow(u"Category:", self.catInput)
        layout.addLayout(formLayout)
        
        errorLayout = QHBoxLayout()
        errorLayout.setContentsMargins(0, 0, 0, 0)
        
        try:
            from PyQt4.QtGui import QCommonStyle, QStyle
            style = QCommonStyle()
            self._errorPixmap = style.standardIcon(QStyle.SP_MessageBoxCritical).pixmap(14,14)
            self._warningPixmap = style.standardIcon(QStyle.SP_MessageBoxWarning).pixmap(14,14)
        except:
            self._errorPixmap = QIcon(get_settings().get_resource("images", "error.png")).pixmap(14,14)
            self._warningPixmap = QIcon(get_settings().get_resource("images", "warning.png")).pixmap(14,14)
        
        self._errorIconLabel = QLabel(self)
        self._errorIconLabel.setAlignment(Qt.AlignCenter)
        self._errorIconLabel.setVisible(False)
        errorLayout.addWidget(self._errorIconLabel, 0, Qt.AlignLeft)
        
        self._errorLabel = QLabel(self)
        self._errorLabel.setVisible(False)
        errorLayout.addWidget(self._errorLabel, 1, Qt.AlignLeft)
        layout.addLayout(errorLayout)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttonBox.accepted.connect(self.checkOK)
        buttonBox.rejected.connect(self.reject)
        
        layout.addWidget(buttonBox, 0, Qt.AlignRight)
        
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        
    def _error(self, msg, warning=False):
        self._errorIconLabel.setPixmap(self._warningPixmap if warning else self._errorPixmap)
        self._errorIconLabel.setVisible(True)
        self._errorLabel.setText(msg)
        self._errorLabel.setVisible(True)
        
    @classmethod
    def _getURLRegex(cls):
        if cls._urlRegex is None:
            cls._urlRegex = re.compile(
                r'^(?:http|ftp)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
                r'localhost|' # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|' # ...or ipv4
                r'\[?[A-F0-9]*:[A-F0-9:]+\]?)' # ...or ipv6
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return cls._urlRegex
        
    def checkOK(self):
        urlText = convert_string(self.urlInput.text()) 
        if len(urlText) == 0:
            self._error(u"Please enter an image URL.")
        elif self._getURLRegex().match(urlText) is None:
            urlText = u"http://" + urlText
            if self._getURLRegex().match(urlText) is not None:
                self.urlInput.setText(urlText)
                self.accept()
            else:
                self._error(u"The entered image URL is not a valid URL.")
        else:
            self.accept()
        
    def getURL(self):
        return convert_string(self.urlInput.text())
    
    def getDescription(self):
        return convert_string(self.descInput.text())
    
    def getCategory(self):
        return convert_string(self.catInput.text())

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = RemotePicturesDialog(None, None, None)
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()

