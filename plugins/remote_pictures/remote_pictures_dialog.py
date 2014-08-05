from PyQt4.QtGui import QLabel, QLineEdit, QFormLayout
from lunchinator import get_peers, convert_string
import re
from lunchinator.error_message_dialog import ErrorMessageDialog

class RemotePicturesDialog(ErrorMessageDialog):
    _urlRegex = None
    
    def __init__(self, parent, peerID, peerInfo):
        if get_peers() is not None:
            self._peerName = get_peers().getDisplayedPeerName(pID=peerID)
        else:
            self._peerName = "<peer name here>"
        self._peerInfo = peerInfo
        
        super(RemotePicturesDialog, self).__init__(parent)

    def _initDone(self):
        if self._peerInfo is None or not u"RP_v" in self._peerInfo:
            self._error("%s might not be able to receive remote pictures." % self._peerName, True)
        
    def _initInputUI(self, layout):
        self.setWindowTitle(u"Send Remote Picture")
        messageLabel = QLabel(u"Send a remote picture to %s" % self._peerName, self)
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
        
    def _checkOK(self):
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

