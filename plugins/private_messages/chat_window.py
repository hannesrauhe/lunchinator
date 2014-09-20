from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QMainWindow, QIcon

from lunchinator import get_notification_center, convert_string, get_settings
from private_messages.chat_widget import ChatWidget


class ChatWindow(QMainWindow):
    windowClosing = pyqtSignal(object) # other's peer ID
    
    def __init__(self, parent, logger, ownName, otherName, ownPicFile, otherPicFile, otherID, sendAction):
        super(ChatWindow, self).__init__(parent)
        self.logger = logger
        self._otherID = otherID
        self._chatWidget = ChatWidget(self, logger, ownName, otherName, ownPicFile, otherPicFile, otherID, sendAction)
        self.setCentralWidget(self._chatWidget)
        self.setWindowTitle(otherName)
        self.setWindowIcon(QIcon(get_settings().get_resource("images", "lunchinator_chat.png")))
        
        get_notification_center().connectDisplayedPeerNameChanged(self._displayedPeerNameChanged)

    def _displayedPeerNameChanged(self, pID, newName, _infoDict):
        pID = convert_string(pID)
        if pID == self._otherID:
            self.setWindowTitle(newName)

    def closeEvent(self, event):
        if not self.getChatWidget().canClose():
            event.ignore()
        else:
            self.windowClosing.emit(self._otherID)
            get_notification_center().disconnectDisplayedPeerNameChanged(self._displayedPeerNameChanged)
            self.getChatWidget().finish()
            event.accept()
    
    def getChatWidget(self):
        return self._chatWidget
