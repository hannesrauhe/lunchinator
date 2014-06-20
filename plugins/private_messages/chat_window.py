from PyQt4.QtGui import QMainWindow
from private_messages.chat_widget import ChatWidget
from PyQt4.QtCore import pyqtSignal

class ChatWindow(QMainWindow):
    windowClosing = pyqtSignal(unicode) # other's peer ID
    
    def __init__(self, parent, ownName, otherName, ownPicFile, otherPicFile, otherID):
        super(ChatWindow, self).__init__(parent)
        self._otherID = otherID
        self._chatWidget = ChatWidget(self, ownName, otherName, ownPicFile, otherPicFile, otherID)
        self.setCentralWidget(self._chatWidget)
        self.setWindowTitle(otherName)

    def closeEvent(self, event):
        if not self.getChatWidget().canClose():
            event.ignore()
        else:
            self.windowClosing.emit(self._otherID)
            event.accept()
    
    def getChatWidget(self):
        return self._chatWidget
