from PyQt4.QtGui import QDialog, QLabel, QVBoxLayout, QHBoxLayout,\
    QWidget, QPushButton, QButtonGroup, QRadioButton, QDialogButtonBox
from PyQt4.Qt import Qt
from functools import partial
from lunchinator.privacy.privacy_settings import PrivacySettings

class PrivacyConfirmationDialog(QDialog):
    POLICY_ONCE = 0
    POLICY_FOREVER = 1
    
    SCOPE_PEER_CATEGORY = 0
    SCOPE_PEER = 1
    SCOPE_EVERYONE_CATEGORY = 2
    SCOPE_EVERYONE = 3
    
    def __init__(self, parent, title, message, peerName, peerID, action, category=None):
        super(PrivacyConfirmationDialog, self).__init__(parent)
        
        self._peerID = peerID
        self._action = action
        self._category = category
        
        layout = QVBoxLayout(self)
        
        messageLabel = QLabel(message, self)
        messageLabel.setWordWrap(True)

        policyWidget = self._initPolicyWidget()
        scopeWidget = self._initScopeWidget(peerName, category)
        buttonBox = self._initButtonBox()
        
        layout.addWidget(messageLabel)
        layout.addWidget(policyWidget, 0)
        layout.addWidget(scopeWidget)
        layout.addWidget(buttonBox, 1)
        
        self.setWindowTitle(title)
        size = self.sizeHint()
        self.setMaximumHeight(size.height())
        
        self._setPolicy(0)
        self._setScope(0)
        
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
        
        if category is None:
            thisPeer = QRadioButton(peerName, scopeWidget)
            thisPeer.clicked.connect(partial(self._setScope, self.SCOPE_PEER))
            self._scopeGroup.addButton(thisPeer)
            
            everyone = QRadioButton(u"Everyone", scopeWidget)
            everyone.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE))
            self._scopeGroup.addButton(everyone)
        else:
            b = QRadioButton(u"%s, category %s" % (peerName, category), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_PEER_CATEGORY))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"%s, all categories" % (peerName), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_PEER))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"Everyone, category %s" % (category), scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE_CATEGORY))
            self._scopeGroup.addButton(b)
            
            b = QRadioButton(u"Everyone, all categories", scopeWidget)
            b.clicked.connect(partial(self._setScope, self.SCOPE_EVERYONE))
            self._scopeGroup.addButton(b)

        self._scopeGroup.buttons()[0].setChecked(True)        
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
        
    def _storeDecision(self):
        # store decision
        if self._category is None:
            if self._scope == self.SCOPE_PEER:
                PrivacySettings.get().addException(self._action,
                                                   None,
                                                   PrivacySettings.POLICY_NOBODY_EX,
                                                   self._peerID,
                                                   1 if self.accepted() else 0)
            elif self._scope == self.SCOPE_EVERYONE:
                PrivacySettings.get().setPolicy(self._action,
                                                None,
                                                PrivacySettings.POLICY_EVERYBODY if self.accepted() else PrivacySettings.POLICY_NOBODY)
        else:
            if self._scope == self.SCOPE_PEER_CATEGORY:
                PrivacySettings.get().addException(self._action,
                                                   self._category,
                                                   PrivacySettings.POLICY_NOBODY_EX,
                                                   self._peerID,
                                                   1 if self.accepted() else 0)
            elif self._scope == self.SCOPE_PEER:
                PrivacySettings.get().addException(self._action,
                                                   None,
                                                   PrivacySettings.POLICY_PEER_EXCEPTION,
                                                   self._peerID,
                                                   1 if self.accepted() else 0)
            elif self._scope == self.SCOPE_EVERYONE_CATEGORY:
                PrivacySettings.get().setPolicy(self._action,
                                                self._category,
                                                PrivacySettings.POLICY_EVERYBODY if self.accepted() else PrivacySettings.POLICY_NOBODY)
            elif self._scope == self.SCOPE_EVERYONE:
                PrivacySettings.get().setPolicy(self._action,
                                                None,
                                                PrivacySettings.POLICY_EVERYBODY if self.accepted() else PrivacySettings.POLICY_NOBODY)
            
    def accept(self):
        if self._action is not None and self._policy == self.POLICY_FOREVER:
            self._storeDecision()
        return QDialog.accept(self)
    
    def reject(self):
        if self._action is not None and self._policy == self.POLICY_FOREVER:
            self._storeDecision()
        return QDialog.reject(self)
        
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys

    app = QApplication(sys.argv)
    window = TimespanInputDialog(None,
                                 "Confirmation",
                                 "Some guy wants to do something in some category, do you approve?",
                                 "Some guy",
                                 "guy'sID",
                                 None,
                                 "Weird")
    
    window.showNormal()
    window.raise_()
    window.activateWindow()
    
    app.exec_()

    print window.result(), window._scope, window._policy
