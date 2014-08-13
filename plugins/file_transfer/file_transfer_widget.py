from PyQt4.QtGui import QWidget, QTreeWidget, QVBoxLayout, QLabel, QProgressBar,\
    QTreeWidgetItem, QFrame, QHBoxLayout, QPushButton, QSizePolicy,\
    QPixmap, QFileIconProvider, QToolButton, QMenu
from PyQt4.Qt import Qt
from lunchinator.utilities import getPlatform, PLATFORM_MAC, revealFile,\
    openFile
from lunchinator import get_settings, get_peers, log_warning, log_error
from PyQt4.QtCore import pyqtSlot, QVariant, QFileInfo, pyqtSignal, QThread
import os
from functools import partial

class _TransferWidget(QFrame):
    cancel = pyqtSignal()
    retry = pyqtSignal(object, object, int) # file path, peerID, transfer ID
    
    def __init__(self, parent, filePath, peerID, transferID, down):
        super(_TransferWidget, self).__init__(parent)
        
        self._filePath = filePath
        self._peerID = peerID
        self._transferID = transferID
        self._transferring = True
        self._down = down
        self._success = False
        
        self._initLayout(filePath)
        
        self._setName(os.path.basename(filePath))
        self.reset()
        
    def _initLayout(self, filePath):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        nameLayout = QHBoxLayout()
        nameLayout.setContentsMargins(0, 0, 0, 0)
        
        fileInfo = QFileInfo(filePath)
        iconProvider = QFileIconProvider()
        icon = iconProvider.icon(fileInfo)
        fileIconLabel = QLabel(self)
        fileIconLabel.setPixmap(icon.pixmap(16,16))
        nameLayout.addWidget(fileIconLabel, 0, Qt.AlignLeft)
        
        self._nameLabel = QLabel(self)
        nameLayout.addSpacing(5)
        nameLayout.addWidget(self._nameLabel, 1, Qt.AlignLeft)
        
        layout.addLayout(nameLayout)
        
        progressWidget = QWidget(self)
        progressLayout = QHBoxLayout(progressWidget)
        progressLayout.setSpacing(5)
        progressLayout.setContentsMargins(0, 0, 0, 0)
        
        iconLabel = QLabel(progressWidget)
        if self._down:
            picFile = get_settings().get_resource("images", "down.png")
        else:
            picFile = get_settings().get_resource("images", "up.png")
        iconLabel.setPixmap(QPixmap(picFile))
        iconLabel.setFixedSize(15,15)
        progressLayout.addWidget(iconLabel, 0, Qt.AlignBottom)
        
        self._progress = QProgressBar(progressWidget)
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        if getPlatform() == PLATFORM_MAC:
            self._progress.setAttribute(Qt.WA_MacMiniSize)
            self._progress.setMaximumHeight(16)
        progressLayout.addWidget(self._progress, 1)
        
        self._button = QPushButton(progressWidget)
        self._button.clicked.connect(self._buttonClicked)
        progressLayout.addSpacing(5)
        progressLayout.addWidget(self._button, 0, Qt.AlignCenter)
        
        layout.addWidget(progressWidget, 0, Qt.AlignBottom)
        
        self._statusLabel = QLabel(self)
        if getPlatform() == PLATFORM_MAC:
            self._statusLabel.setAttribute(Qt.WA_MacSmallSize)
        layout.addWidget(self._statusLabel)
        
        self.setObjectName(u"__transfer_widget")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame#__transfer_widget{border-width: 1px; border-top-style: none; border-right-style: none; border-bottom-style: solid; border-left-style: none; border-color:palette(mid)}");
            
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        
    def reset(self):
        self._transferring = True
        self._statusLabel.setText(u"Waiting for data..." if self._down else u"Waiting for peer...")
        self._checkButtonFunction()
        self._progress.setMaximum(0)
        
    def isFinished(self):
        return not self._transferring
    
    def isSuccessful(self):
        return self._success
    
    def getFilePath(self):
        return self._filePath
        
    def _setName(self, name):
        if self._down:
            text = u"%s \u2190 %s"
        else:
            text = u"%s \u2192 %s"
        
        if get_peers() is not None:
            peerName = get_peers().getDisplayedPeerName(self._peerID)
        else:
            peerName = u"<unknown peer>"
        self._nameLabel.setText(text % (name, peerName))
        
    def _setIcon(self, baseName):
        if baseName is None:
            self._button.setStyleSheet("""
                QPushButton {min-width: 15px;
                             max-width: 15px;
                             min-height: 15px;
                             max-height: 15px;
                             margin: 0px;
                             padding: 0px;
                             border:none;
                }
            """)
        else:
            defPath = get_settings().get_resource("images", "%s32.png" % baseName)
            pressPath = get_settings().get_resource("images", "%s32p.png" % baseName)
            self._button.setStyleSheet("""
                QPushButton {min-width: 15px;
                             max-width: 15px;
                             min-height: 15px;
                             max-height: 15px;
                             margin: 0px;
                             padding: 0px;
                             border:none;
                             border-image: url(%s);
                }
                QPushButton:pressed {
                             border-image: url(%s);
                }
            """ % (defPath, pressPath)
            )
        
    def _checkButtonFunction(self):
        if self._transferring:
            self._setIcon("cancel")
        elif self._down:
            if self._success:
                self._setIcon("reveal")
            else:
                self._setIcon(None)
        else:
            if self._success:
                self._setIcon("reveal")
            else:
                self._setIcon("retry")
    
    def _buttonClicked(self):
        if self._transferring:
            self.cancel.emit()
        elif self._down:
            if self._success:
                revealFile(self._filePath)
        else:
            if self._success:
                revealFile(self._filePath)
            else:
                self.retry.emit(self._filePath, self._peerID, self._transferID)
        
    def connect(self, dataThread):        
        dataThread.progressChanged.connect(self.progressChanged)
        dataThread.errorOnTransfer.connect(self.transferError)
        dataThread.successfullyTransferred.connect(self.successfullyTransferred)
        dataThread.transferCanceled.connect(self.transferCanceled)
        self.cancel.connect(dataThread.cancelTransfer)

    def disconnect(self, dataThread):
        dataThread.progressChanged.disconnect(self.progressChanged)
        dataThread.errorOnTransfer.disconnect(self.transferError)
        dataThread.successfullyTransferred.disconnect(self.successfullyTransferred)
        dataThread.transferCanceled.disconnect(self.transferCanceled)
        self.cancel.disconnect(dataThread.cancelTransfer)
    
    @pyqtSlot(int, int)
    def progressChanged(self, newVal, maxVal):
        if newVal is 0:
            self._transferring = True
            self._progress.setMaximum(maxVal)
            self._statusLabel.setText(u"Receiving data" if self._down else u"Sending data")
        self._progress.setValue(newVal)
    
    @pyqtSlot(QThread, object)
    def successfullyTransferred(self, thread, _path):
        self._transferring = False
        self._success = True
        self._statusLabel.setText(u"Transfer finished successfully")
        self.disconnect(thread)
        self._checkButtonFunction()
    
    @pyqtSlot(object)    
    def transferError(self, thread, message):
        self._transferring = False
        self._statusLabel.setText(u"Error transferring file (%s)" % message)
        self.disconnect(thread)
        self._checkButtonFunction()
        
    @pyqtSlot(object)
    def transferCanceled(self, thread):
        self._transferring = False
        self._statusLabel.setText(u"Transfer canceled")
        self.disconnect(thread)
        self._checkButtonFunction()
        
    def transferTimedOut(self):
        self._progress.setMaximum(100)
        self._transferring = False
        self._statusLabel.setText(u"Transfer timed out")
        self._checkButtonFunction()

class DeleteKeyTreeWidget(QTreeWidget):
    deletePressed = pyqtSignal()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.deletePressed.emit()
            event.accept()
        else:
            QTreeWidget.keyPressEvent(self, event)

class FileTransferWidget(QWidget):
    _TRANSFER_ID_ROLE = Qt.UserRole + 1
    _PEER_ID_ROLE = _TRANSFER_ID_ROLE + 1
    _IS_OUTGOING = _PEER_ID_ROLE + 1
    
    retry = pyqtSignal(object, object, int) # file path, peerID, transfer ID (forwarded from transfer widget)
    
    def __init__(self, parent, delegate):
        super(FileTransferWidget, self).__init__(parent)
        
        self._delegate = delegate
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._initTopView(), 0)
        layout.addWidget(self._initCentralView(), 1)
        
    def _initTopView(self):
        topWidget = QWidget(self)
        
        self._sendFileButton = QToolButton(topWidget)
        self._sendFileButton.setText(u"Send file to ")
        self._sendFileButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._sendFileButton.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self._sendFileButton)
        menu.aboutToShow.connect(partial(self._fillPeersPopup, menu))
        self._sendFileButton.setMenu(menu)
            
        self._clearButton = QPushButton("Clear Inactive", topWidget)
        self._clearButton.clicked.connect(self._clearFinished)
        
        layout = QHBoxLayout(topWidget)
        layout.setContentsMargins(10, 10, 10, 0)
        layout.addWidget(self._sendFileButton, 1, Qt.AlignLeft)
        layout.addWidget(self._clearButton, 0, Qt.AlignLeft)
        return topWidget
    
    def _initCentralView(self):
        self._transferList = DeleteKeyTreeWidget(self)
        self._transferList.setColumnCount(1)
        self._transferList.setAlternatingRowColors(False)
        self._transferList.setHeaderHidden(True)
        self._transferList.setItemsExpandable(False)
        self._transferList.setIndentation(0)
        self._transferList.setSelectionMode(QTreeWidget.SingleSelection)
        self._transferList.itemDoubleClicked.connect(self._itemDoubleClicked)
        self._transferList.deletePressed.connect(self._deletePressed)
        
        return self._transferList
    
    def _checkRemove(self, idx):
        item = self._transferList.topLevelItem(idx)
        widget = self._transferList.itemWidget(item, 0)
        if widget.isFinished():
            self._transferList.takeTopLevelItem(idx)
    
    @pyqtSlot()
    def _clearFinished(self):
        for idx in xrange(self._transferList.topLevelItemCount() - 1, -1, -1):
            self._checkRemove(idx)
    
    @pyqtSlot()
    def _deletePressed(self):
        selection = self._transferList.selectedIndexes()
        for index in reversed(selection):
            self._checkRemove(index.row())
    
    @pyqtSlot(QTreeWidgetItem, int)
    def _itemDoubleClicked(self, item, col):
        widget = self._transferList.itemWidget(item, col)
        if widget.isFinished() and widget.isSuccessful():
            openFile(widget.getFilePath())
    
    def _fillPeersPopup(self, menu):
        menu.clear()
        
        if get_peers() is None:
            log_warning("no lunch_peers instance available, cannot show peer actions")
            return
        
        with get_peers():
            for peerID in get_peers():
                peerInfo = get_peers().getPeerInfo(pID=peerID, lock=False)
                if self._delegate.getSendFileAction().appliesToPeer(peerID, peerInfo):
                    menu.addAction(get_peers().getDisplayedPeerName(pID=peerID, lock=False), partial(self._sendFile, peerID))
        
    def _sendFile(self, peerID):
        peerInfo = get_peers().getPeerInfo(pID=peerID)
        if peerInfo is None:
            log_error("cannot send file to offline peer")
            return
        self._delegate.getSendFileAction().performAction(peerID, peerInfo, self)
        
    @pyqtSlot(object, object, int)
    def _retry(self, filePath, peerID, transferID):
        self.retry.emit(filePath, peerID, transferID)
    
    def _addTransfer(self, filePath, transferID, peerID, down):
        item = QTreeWidgetItem(self._transferList)
        item.setData(0, self._TRANSFER_ID_ROLE, QVariant(transferID))
        item.setData(0, self._PEER_ID_ROLE, QVariant(peerID))
        item.setData(0, self._IS_OUTGOING, QVariant(not down))
        
        self._transferList.addTopLevelItem(item)
        widget = _TransferWidget(self._transferList, filePath, peerID, transferID, down)
        widget.retry.connect(self._retry)
        self._transferList.setItemWidget(item, 0, widget)
        return widget
        
    def _getOutgoingTransferItem(self, transferID):
        for idx in xrange(self._transferList.topLevelItemCount()):
            item = self._transferList.topLevelItem(idx)
            if item.data(0, self._IS_OUTGOING).toBool() and \
               item.data(0, self._TRANSFER_ID_ROLE).toInt()[0] == transferID:
                return item
        return None
        
    @pyqtSlot(int, object, object, bool)
    def startOutgoingTransfer(self, transferID, peerID, path, isRetry):
        if isRetry:
            item = self._getOutgoingTransferItem(transferID)
            if item is not None:
                widget = self._transferList.itemWidget(item, 0)
                widget.reset()
                return
        self._addTransfer(path, transferID, peerID, False)
    
    @pyqtSlot(int, object)
    def outgoingTransferStarted(self, transferID, dataThread):
        item = self._getOutgoingTransferItem(transferID)
        if item is not None:
            widget = self._transferList.itemWidget(item, 0)
            widget.connect(dataThread)
            
    @pyqtSlot(int)
    def outgoingTransferTimedOut(self, transferID):
        item = self._getOutgoingTransferItem(transferID)
        if item is not None:
            widget = self._transferList.itemWidget(item, 0)
            widget.transferTimedOut()
    
    @pyqtSlot(object, int, object, object)
    def incomingTransferStarted(self, peerID, transferID, filePath, dataThread):
        widget = self._addTransfer(filePath, transferID, peerID, True)
        widget.connect(dataThread)
    