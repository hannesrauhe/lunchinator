from PyQt4.QtGui import QWidget, QVBoxLayout, QLabel, QPushButton, \
                        QTreeView, QHBoxLayout, QStandardItemModel, QColor,\
                        QStandardItem, QItemSelection, QHeaderView
from PyQt4.QtCore import pyqtSignal, Qt
from lunchinator import get_settings, convert_string
from lunchinator.git import GitHandler
from lunchinator.log.logging_slot import loggingSlot
    
class PluginRepositoriesGUI(QWidget):
    PATH_COLUMN = 1
    ACTIVE_COLUMN = 0
    AUTO_UPDATE_COLUMN = 2
    STATUS_COLUMN = 3
    
    addRepository = pyqtSignal()
    checkForUpdates = pyqtSignal()
    
    def __init__(self, logger, parent):
        super(PluginRepositoriesGUI, self).__init__(parent)
       
        self.logger = logger
        self._gitHandler = GitHandler(logger)
        
        layout = QVBoxLayout(self)
        
        self._reposTable = QTreeView(self) 
        self._reposTable.setIndentation(0)
        self._reposTable.header().setStretchLastSection(False)
                
        self._reposModel = QStandardItemModel(self._reposTable)
        self._initModel()
        self._reposTable.setModel(self._reposModel)
        
        self._reposTable.setSelectionMode(QTreeView.ExtendedSelection)
        self._reposTable.selectionModel().selectionChanged.connect(self._selectionChanged)
        
        layout.addWidget(self._reposTable)

        buttonLayout = QHBoxLayout()    
        addButton = QPushButton("Add...")
        addButton.clicked.connect(self.addRepository)
        self._removeButton = QPushButton("Remove")
        self._removeButton.setEnabled(False)
        self._removeButton.clicked.connect(self._removeSelected)
        refreshButton = QPushButton("Check Status")
        refreshButton.clicked.connect(self.checkForUpdates)
        buttonLayout.addWidget(addButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(refreshButton)
        
        layout.addLayout(buttonLayout)
        
        self._statusWidget = QWidget(self) 
        self._statusWidget.setVisible(False)
        statusLayout = QHBoxLayout(self._statusWidget)
        statusLayout.setContentsMargins(0, 0, 0, 0)
        self._statusLabel = QLabel(self)
        statusLayout.addWidget(self._statusLabel)
        layout.addWidget(self._statusWidget)
        
    def clear(self):
        self._initModel()
        
    def _updateStatusItem(self, item, path, outdated=None, upToDate=None):
        # first check fresh results, then the ones from repositories
        if upToDate and path in upToDate:
            item.setText(upToDate[path])
            if upToDate[path] == GitHandler.UP_TO_DATE_REASON:
                item.setData(QColor(0, 255, 0), Qt.DecorationRole)
            else:
                item.setData(QColor(255, 0, 0), Qt.DecorationRole)
        elif outdated and path in outdated:
            item.setText("Repository can be updated")
            item.setData(QColor(255, 215, 0), Qt.DecorationRole)
        elif get_settings().get_plugin_repositories().isUpToDate(path):
            item.setText("No updates (for details, check status)")
            item.setData(QColor(0, 255, 0), Qt.DecorationRole)
        elif get_settings().get_plugin_repositories().isOutdated(path):
            item.setText("Repository can be updated")
            item.setData(QColor(255, 215, 0), Qt.DecorationRole)
        else:
            item.setData(None, Qt.DecorationRole)
        
    def updateStatusItems(self, outdated=None, upToDate=None):
        for row in xrange(self._reposModel.rowCount()):
            path = convert_string(self._reposModel.item(row, self.PATH_COLUMN).data(Qt.DisplayRole).toString())
            self._updateStatusItem(self._reposModel.item(row, self.STATUS_COLUMN), path, outdated, upToDate)
        
    def _initModel(self):
        from PyQt4.QtCore import QStringList
        self._reposModel.clear()
        stringList = QStringList([u"Active", u"Path", u"Auto Update", u"Status"])
        self._reposModel.setColumnCount(stringList.count())
        self._reposModel.setHorizontalHeaderLabels(stringList)
        
    def appendRepository(self, path, active, autoUpdate, canAutoUpdate = None):
        activeItem = QStandardItem()
        activeItem.setEditable(False)
        activeItem.setCheckState(Qt.Checked if active else Qt.Unchecked)
        activeItem.setCheckable(True)
        
        pathItem = QStandardItem()
        pathItem.setData(path, Qt.DisplayRole)
        pathItem.setEditable(False)
        
        autoUpdateItem = QStandardItem()
        autoUpdateItem.setEditable(False)
        if canAutoUpdate == None:
            canAutoUpdate = self._gitHandler.hasGit(path)
        if canAutoUpdate:
            autoUpdateItem.setCheckState(Qt.Checked if autoUpdate else Qt.Unchecked)
            autoUpdateItem.setCheckable(True)
                
        statusItem = QStandardItem()
        self._updateStatusItem(statusItem, path)
                
        self._reposModel.appendRow([activeItem, pathItem, autoUpdateItem, statusItem])
        
    def resizeColumns(self):
        self._reposTable.resizeColumnToContents(self.ACTIVE_COLUMN)
        self._reposTable.resizeColumnToContents(self.AUTO_UPDATE_COLUMN)
        self._reposTable.header().setResizeMode(self.PATH_COLUMN, QHeaderView.Stretch)
        self._reposTable.header().setResizeMode(self.STATUS_COLUMN, QHeaderView.ResizeToContents)
    
    def getTable(self):
        return self._reposTable
    
    @loggingSlot(QItemSelection, QItemSelection)
    def _selectionChanged(self, _sel, _desel):
        selection = self._reposTable.selectionModel().selectedRows()
        self._removeButton.setEnabled(len(selection) > 0)
        
    @loggingSlot()
    def _removeSelected(self):
        selection = self._reposTable.selectionModel().selectedRows()
        for index in selection:
            self._reposTable.model().removeRow(index.row())
        
    def setStatus(self, msg, _progress=False):
        if msg:
            self._statusLabel.setText(msg)
            self._statusWidget.setVisible(True)
        else:
            self._statusWidget.setVisible(False)