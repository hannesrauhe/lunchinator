from PyQt4.QtGui import QDialog, QLabel, QVBoxLayout, QHBoxLayout,\
    QWidget, QPushButton, QButtonGroup, QRadioButton, QDialogButtonBox
from PyQt4.Qt import Qt
from functools import partial
from lunchinator.privacy.privacy_settings import PrivacySettings
from PyQt4.QtCore import QTimer
from lunchinator.log.logging_slot import loggingSlot

class PrivacyConfirmationDialog(QDialog):
    POLICY_ONCE = 0
    POLICY_FOREVER = 1
    
    SCOPE_PEER_CATEGORY = 0
    SCOPE_PEER = 1
    SCOPE_EVERYONE_CATEGORY = 2
    SCOPE_EVERYONE = 3
    
    def __init__(self, parent, title, peerName, peerID, action, category, msgData, timeout=None):
        super(PrivacyConfirmationDialog, self).__init__(parent)
        
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self._peerID = peerID
        self._peerName = peerName
        self._action = action
        self._category = category if category is not None else PrivacySettings.NO_CATEGORY
        self._useCategories = self._action.usesPrivacyCategories()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        
        messageLabel = QLabel(self._createMessage(msgData), self)
        messageLabel.setWordWrap(True)

        policyWidget = self._initPolicyWidget()
        scopeWidget = self._initScopeWidget(peerName, category)
        buttonBox = self._initButtonBox()
        
        bottomWidget = QWidget(self)
        bottomLayout = QHBoxLayout(bottomWidget)
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        bottomLayout.setSpacing(0)
        self._timeoutLabel = QLabel(bottomWidget)
        bottomLayout.addWidget(self._timeoutLabel, 1)
        bottomLayout.addWidget(buttonBox)
        
        layout.addWidget(messageLabel)
        layout.addWidget(policyWidget, 0)
        layout.addWidget(scopeWidget)
        layout.addWidget(bottomWidget, 1)
        
        self.setWindowTitle(title)
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        
        self._setPolicy(0)
        if timeout:
            self._timeout = timeout
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._decrementTimer)
            self._timer.start(1000)
        else:
            self._timer = None
    
    @loggingSlot()
    def _decrementTimer(self):
        self._timeout -= 1
        if self._timeout == 0:
            self.reject()
        self._timeoutLabel.setText(u"%d s" % self._timeout)
            
    def _createMessage(self, msgData):
        message = self._action.getConfirmationMessage(self._peerID, self._peerName, msgData)
        if message is None:
            # create default message
            if self._action.usesPrivacyCategories():
                if self._category == PrivacySettings.NO_CATEGORY:
                    message = "%s wants to perform the following action: %s (uncategorized)" % (self._peerName, self._action.getName())
                else:
                    message = "%s wants to perform the following action: %s, in category %s" % (self._peerName, self._action.getName(), self._category)
            else:
                message = "%s wants to perform the following action: %s" % (self._peerName, self._action.getName())
        return message
        
    def _initPolicyWidget(self):
        policyWidget = QWidget(self)
        self._policyGroup = QButtonGroup(self)
        
        once = QRadioButton("Once", policyWidget)
        once.setChecked(True)
        once.clicked.connect(partial(self._setPolicy, self.POLICY_ONCE))
        self._policyGroup.addButton(once)
        
        forever = QRadioButton("Forever", policyWidget)
        forever.clicked.connect(partial(self._setPolicy, self.POLICY_FOREVER))
        self._policyGroup.addButton(forever)
        
        policyLayout = QHBoxLayout(policyWidget)
        policyLayout.setContentsMargins(5, 0, 5, 0)
        policyLayout.addWidget(once, 0)
        policyLayout.addWidget(forever, 1, Qt.AlignLeft)
        return policyWidget
    
    def _initScopeWidget(self, peerName, category):
        scopeWidget = QWidget(self)
        self._scopeGroup = QButtonGroup(self)
        
        if not self._useCategories:
            thisPeer = QRadioButton(peerName, scopeWidget)
            thisPeer.clicked.connect(partial(self._setScope, self.SCOPE_PEER))
            self._scopeGroup.addButton(thisPeer)
            
            everyone = QRadioButton(u"Everyone", scopeWidget)
            everyone.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE))
            self._scopeGroup.addButton(everyone)
        else:
            if self._category == PrivacySettings.NO_CATEGORY:
                catDesc = u"uncategorized"
            else:
                catDesc = u"category %s" % category
            
            b = QRadioButton(u"%s, %s" % (peerName, catDesc), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_PEER_CATEGORY))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"%s, all categories" % (peerName), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_PEER))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"Everyone, %s" % (catDesc), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE_CATEGORY))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"Everyone, all categories", scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE))
            self._scopeGroup.addButton(b)

        self._scopeGroup.buttons()[0].click()        
        scopeLayout = QVBoxLayout(scopeWidget)
        scopeLayout.setContentsMargins(5, 0, 5, 0)
        for button in self._scopeGroup.buttons():
            scopeLayout.addWidget(button, 0)
        return scopeWidget

    def _initButtonBox(self):
        cancelButton = QPushButton("Deny", self)
        cancelButton.clicked.connect(self.reject)
        
        okButton = QPushButton("Accept", self)
        okButton.clicked.connect(self.accept)
        
        buttonBox = QDialogButtonBox(Qt.Horizontal, self)
        buttonBox.addButton(cancelButton, QDialogButtonBox.RejectRole)
        buttonBox.addButton(okButton, QDialogButtonBox.AcceptRole)
        return buttonBox

    def _setPolicy(self, policy):
        self._policy = policy
        for button in self._scopeGroup.buttons():
            button.setEnabled(policy == self.POLICY_FOREVER)
        
    def _setScope(self, scope):
        self._scope = scope
        
    def _clickNext(self, group):
        curIdx = group.buttons().index(group.checkedButton())
        if curIdx + 1 < len(group.buttons()):
            group.buttons()[curIdx + 1].click()
            
    def _clickPrev(self, group):
        curIdx = group.buttons().index(group.checkedButton())
        if curIdx - 1 >= 0:
            group.buttons()[curIdx - 1].click()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right:
            self._clickNext(self._policyGroup)
            event.accept()
        elif event.key() == Qt.Key_Left:
            self._clickPrev(self._policyGroup)
            event.accept()
        elif event.key() == Qt.Key_Up:
            self._clickPrev(self._scopeGroup)
            event.accept()
        elif event.key() == Qt.Key_Down:
            self._clickNext(self._scopeGroup)
            event.accept()
        else:
            return QDialog.keyPressEvent(self, event)
        
    def _storeDecision(self, accepted):
        # store decision
        if not self._useCategories:
            if self._scope == self.SCOPE_PEER:
                PrivacySettings.get().addException(self._action,
                                                   None,
                                                   PrivacySettings.POLICY_NOBODY_EX,
                                                   self._peerID,
                                                   1 if accepted else 0,
                                                   categoryPolicy=PrivacySettings.CATEGORY_NEVER)
            elif self._scope == self.SCOPE_EVERYONE:
                PrivacySettings.get().setPolicy(self._action,
                                                None,
                                                PrivacySettings.POLICY_EVERYBODY if accepted else PrivacySettings.POLICY_NOBODY,
                                                categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        else:
            if self._scope == self.SCOPE_PEER_CATEGORY:
                PrivacySettings.get().addException(self._action,
                                                   self._category,
                                                   PrivacySettings.POLICY_NOBODY_EX,
                                                   self._peerID,
                                                   1 if accepted else 0,
                                                   categoryPolicy=PrivacySettings.CATEGORY_ALWAYS)
            elif self._scope == self.SCOPE_PEER:
                PrivacySettings.get().addException(self._action,
                                                   None,
                                                   PrivacySettings.POLICY_PEER_EXCEPTION,
                                                   self._peerID,
                                                   1 if accepted else 0,
                                                   categoryPolicy=PrivacySettings.CATEGORY_NEVER)
            elif self._scope == self.SCOPE_EVERYONE_CATEGORY:
                PrivacySettings.get().setPolicy(self._action,
                                                self._category,
                                                PrivacySettings.POLICY_EVERYBODY if accepted else PrivacySettings.POLICY_NOBODY,
                                                categoryPolicy=PrivacySettings.CATEGORY_ALWAYS)
            elif self._scope == self.SCOPE_EVERYONE:
                PrivacySettings.get().setPolicy(self._action,
                                                None,
                                                PrivacySettings.POLICY_EVERYBODY if accepted else PrivacySettings.POLICY_NOBODY,
                                                categoryPolicy=PrivacySettings.CATEGORY_NEVER)
            
    def _finish(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None        
    
    @loggingSlot()
    def accept(self):
        self._finish()
        if self._action is not None and self._policy == self.POLICY_FOREVER:
            self._storeDecision(True)
        return QDialog.accept(self)
    
    @loggingSlot()
    def reject(self):
        self._finish()
        if self._action is not None and self._policy == self.POLICY_FOREVER:
            self._storeDecision(False)
        return QDialog.reject(self)
        
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys
    from lunchinator.peer_actions import PeerAction
    class TestAction(PeerAction):
        def getName(self):
            return u"Test"
        
        def usesPrivacyCategories(self):
            return False

    app = QApplication(sys.argv)
    window = PrivacyConfirmationDialog(None,
                                       "Confirmation",
                                       u"Some guy",
                                       "guy'sID",
                                       TestAction(),
                                       "Weird",
                                       None,
                                       10)
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()

    print window.result(), window._scope, window._policy
