from PyQt4.QtGui import QStandardItemModel
from PyQt4.QtCore import Qt

class ChatMessagesModel(QStandardItemModel):
    STATUS_ICON_ROLE = Qt.UserRole + 1
    OWN_MESSAGE_ROLE = STATUS_ICON_ROLE + 1
    
    def __init__(self, parent):
        super(ChatMessagesModel, self).__init__(parent)
        self.setColumnCount(3)
