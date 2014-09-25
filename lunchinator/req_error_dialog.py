from PyQt4.QtGui import QVBoxLayout, QDialog, QDialogButtonBox, QLabel,\
    QHBoxLayout, QFrame, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt4.QtCore import Qt, QSize, QVariant
from lunchinator.utilities import PLATFORM_MAC, getPlatform
from lunchinator import convert_string
from lunchinator.log.logging_slot import loggingSlot

class RequirementsErrorDialog(QDialog):
    IGNORED = QDialog.Accepted + 1
    _REQUIREMENT_ROLE = Qt.UserRole + 1
    
    def __init__(self, requirements, parent, canInstall, text=None):
        """Constructor
        
        requirements -- List of (requirement (string),
                                 component (string),
                                 reason (string),
                                 optional (bool))
        parent -- parent QWidget
        """
        super(RequirementsErrorDialog, self).__init__(parent, Qt.WindowStaysOnTopHint)
        self._empty = True
        self._requirements = requirements
        self._canInstall = canInstall
        
        self._initUI(text)
        self._addRequirements()
        self._reqTable.resizeColumnToContents(0)
        self._reqTable.resizeColumnToContents(1)
        self.setWindowTitle("Missing Requirements")
        
    def _addRequirements(self):
        for requirement, component, reason, optional in self._requirements:
            item = QTreeWidgetItem()
            item.setCheckState(0, Qt.Checked)
            if not optional:
                item.setFlags(Qt.ItemFlags(int(item.flags()) & ~Qt.ItemIsEnabled))
            item.setText(0, requirement)
            item.setText(1, reason)
            item.setText(2, component)
            item.setData(0, self._REQUIREMENT_ROLE, QVariant(requirement))
            self._reqTable.addTopLevelItem(item)
        
    def getSelectedRequirements(self):
        reqs = []
        for row in xrange(self._reqTable.topLevelItemCount()):
            rowItem = self._reqTable.topLevelItem(row)
            if rowItem.checkState(0) == Qt.Checked:
                reqs.append(convert_string(rowItem.data(0, self._REQUIREMENT_ROLE).toString()))
        return reqs
        
    def sizeHint(self):
        return QSize(400, 200)
        
    def _initUI(self, text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(5)
        
        labelLayout = QHBoxLayout()
        if not text:
            text = u"Some plugins cannot be activated due to missing requirements:"
        label = QLabel(text, self)
        label.setWordWrap(True)
        labelLayout.addWidget(label)
        labelLayout.setContentsMargins(10, 0, 0, 0)
        layout.addLayout(labelLayout)
        
        self._reqTable = QTreeWidget(self)
        self._reqTable.setSortingEnabled(False)
        self._reqTable.setHeaderHidden(False)
        self._reqTable.setAlternatingRowColors(True)
        self._reqTable.setIndentation(0)
        self._reqTable.setUniformRowHeights(True)
        self._reqTable.setObjectName(u"__ERROR_LOG_")
        self._reqTable.setColumnCount(3)
        self._reqTable.setHeaderLabels([u"Package", u"Problem", u"Required by"])
        
        self._reqTable.setFrameShape(QFrame.StyledPanel)
        if getPlatform() == PLATFORM_MAC:
            self._reqTable.setAttribute(Qt.WA_MacShowFocusRect, False)
            self._reqTable.setStyleSheet("QFrame#__ERROR_LOG_{border-width: 1px; border-top-style: solid; border-right-style: none; border-bottom-style: solid; border-left-style: none; border-color:palette(mid)}");
            
        layout.addWidget(self._reqTable)
        
        buttonBox = QDialogButtonBox(Qt.Horizontal, self)
        ignore = QPushButton(u"Ignore", self)
        deactivate = QPushButton(u"Deactivate", self)
        install = QPushButton(u"Install Selected", self)
        install.setEnabled(self._canInstall)
        buttonBox.addButton(deactivate, QDialogButtonBox.DestructiveRole)
        buttonBox.addButton(ignore, QDialogButtonBox.RejectRole)
        buttonBox.addButton(install, QDialogButtonBox.AcceptRole)
        deactivate.clicked.connect(self._deactivate)
        ignore.clicked.connect(self._ignore)
        buttonBox.accepted.connect(self.accept)
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(buttonBox, 1, Qt.AlignRight)
        layout.addLayout(bottomLayout)
        
    @loggingSlot()
    def _deactivate(self):
        self.reject()
        
    @loggingSlot()
    def _ignore(self):
        self.done(self.IGNORED)
            
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys
    from lunchinator.log import initializeLogger
    
    initializeLogger()
    app = QApplication(sys.argv)
    reqs = [(u"someReq > 1.1", u"Plugin 1", "missing", True),
            (u"anotherReq <= 0.4", u"Core", u"wrong version (installed: 0.5)", False)]
    window = RequirementsErrorDialog(reqs, None, True, None)
    
    if window.exec_() == window.Accepted:
        print window.getSelectedRequirements()

