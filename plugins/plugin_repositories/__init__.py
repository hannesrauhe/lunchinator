from lunchinator import get_server, log_warning, convert_string,\
    get_notification_center
from lunchinator.lunch_settings import lunch_settings
from lunchinator.iface_plugins import iface_general_plugin
from lunchinator import log_exception, log_error, log_info, get_settings, log_debug
from lunchinator.utilities import getValidQtParent, displayNotification, \
    getGPG, getPlatform, PLATFORM_WINDOWS, PLATFORM_MAC, PLATFORM_LINUX, which,\
    getApplicationBundle, stopWithCommand
from lunchinator.download_thread import DownloadThread
from lunchinator.shell_thread import ShellThread
import urllib2, sys, os, contextlib, subprocess, json
import tempfile
from functools import partial
from xml.etree import ElementTree
from online_update.gitUpdate import gitUpdate
from lunchinator.git import GitHandler
from lunchinator.callables import AsyncCall
    
class plugin_repositories(iface_general_plugin):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    PATH_COLUMN = 1
    ACTIVE_COLUMN = 0
    AUTO_UPDATE_COLUMN = 2
    STATUS_COLUMN = 3
    
    def __init__(self):
        super(plugin_repositories, self).__init__()
        self._modified = False
    
    def activate(self):
        from PyQt4.QtCore import QTimer
            
        self._scheduleTimer = QTimer(getValidQtParent())
        self._scheduleTimer.timeout.connect(self._checkForUpdates)
        self._scheduleTimer.start(plugin_repositories.CHECK_INTERVAL)
        
        self._checkForUpdates()
        
    def deactivate(self):
        if self._scheduleTimer != None:
            self._scheduleTimer.stop()
            self._scheduleTimer.deleteLater()
        
        iface_general_plugin.deactivate(self)
        
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QStandardItem, QWidget, \
                                QVBoxLayout, QLabel, QSizePolicy, QPushButton, \
                                QTextEdit, QProgressBar, QStackedWidget, QTreeView, \
                                QStandardItemModel, QHBoxLayout
        from PyQt4.QtCore import Qt
       
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self._reposTable = QTreeView(widget) 
        self._reposTable.setIndentation(0)
        
        self._reposModel = QStandardItemModel(self._reposTable)
        self._initModel()
        self._reposTable.setModel(self._reposModel)
        
        self._reposTable.setSelectionMode(QTreeView.MultiSelection)
        self._reposTable.selectionModel().selectionChanged.connect(self._selectionChanged)
        
        layout.addWidget(self._reposTable)

        buttonLayout = QHBoxLayout()    
        addButton = QPushButton("Add...")
        addButton.clicked.connect(partial(self._addRepository, widget))
        self._removeButton = QPushButton("Remove")
        self._removeButton.setEnabled(False)
        self._removeButton.clicked.connect(self._removeSelected)
        refreshButton = QPushButton("Check Status")
        refreshButton.clicked.connect(partial(self._checkForUpdates, True))
        buttonLayout.addWidget(addButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(refreshButton)
        
        layout.addLayout(buttonLayout)
        
        self._initRepositories()
        
        self._reposTable.resizeColumnToContents(self.ACTIVE_COLUMN)
        self._reposTable.resizeColumnToContents(self.AUTO_UPDATE_COLUMN)
        self._reposTable.setColumnWidth(self.PATH_COLUMN, 150)
        
        get_notification_center().registerRepositoryUpdate(self._processUpdates)
        return widget  
    
    def _selectionChanged(self, _sel, _desel):
        selection = self._reposTable.selectionModel().selectedRows()
        self._removeButton.setEnabled(len(selection) > 0)
    
    def _addRepository(self, parent):
        from plugin_repositories.add_repo_dialog import AddRepoDialog
        dialog = AddRepoDialog(parent)
        dialog.exec_()
        if dialog.result() == AddRepoDialog.Accepted:
            self._appendRepository(dialog.getPath(),
                                   dialog.isRepositoryActive(),
                                   dialog.isAutoUpdateEnabled(),
                                   dialog.canAutoUpdate())
            self._modified = True
    
    def _initModel(self):
        from PyQt4.QtCore import QStringList
        self._reposModel.clear()
        stringList = QStringList([u"Active", u"Path", u"Auto Update", u"Status"])
        self._reposModel.setColumnCount(stringList.count())
        self._reposModel.setHorizontalHeaderLabels(stringList)
    
    def _initRepositories(self):
        self._modified = False
        self._initModel()
        for path, active, auto_update in get_settings().get_plugin_repositories().getExternalRepositories():
            if os.path.isdir(path):
                self._appendRepository(path, active, auto_update)
           
    def _updateStatusItem(self, item, path):
        from PyQt4.QtGui import QColor
        from PyQt4.QtCore import Qt
        if get_settings().get_plugin_repositories().isUpToDate(path):
            item.setData(QColor(0, 255, 0), Qt.DecorationRole)
        elif get_settings().get_plugin_repositories().isOutdated(path):
            item.setData(QColor(127, 255, 127), Qt.DecorationRole)
        else:
            item.setData(None, Qt.DecorationRole)
      
    def _appendRepository(self, path, active, autoUpdate, canAutoUpdate = None):
        from PyQt4.QtGui import QStandardItem
        from PyQt4.QtCore import Qt

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
            gitHandler = GitHandler()
            canAutoUpdate = gitHandler.has_git(path)
        if canAutoUpdate:
            autoUpdateItem.setCheckState(Qt.Checked if autoUpdate else Qt.Unchecked)
            autoUpdateItem.setCheckable(True)
                
        statusItem = QStandardItem()
        self._updateStatusItem(statusItem, path)
                
        self._reposModel.appendRow([activeItem, pathItem, autoUpdateItem, statusItem])
        
    def _removeSelected(self):
        selection = self._reposTable.selectionModel().selectedRows()
        for index in selection:
            self._reposModel.removeRow(index.row())
        
    def _checkForUpdatesFinished(self, outdated):
        if len(outdated) > 0:
            get_notification_center().emitRepositoryUpdate()
        
    def _processUpdates(self):
        from PyQt4.QtCore import Qt
        for row in xrange(self._reposModel.rowCount()):
            path = convert_string(self._reposModel.item(row, self.PATH_COLUMN).data(Qt.DisplayRole).toString())
            self._updateStatusItem(self._reposModel.item(row, self.STATUS_COLUMN), path)
        
    def _checkForUpdates(self, forced=False):
        AsyncCall(getValidQtParent(),
                  get_settings().get_plugin_repositories().checkForUpdates,
                  self._checkForUpdatesFinished)(forced)
        
    def discard_changes(self):
        self._initRepositories()
        
    def save_options_widget_data(self):
        if self._modified:
            from PyQt4.QtCore import Qt
            repos = []
            for row in xrange(self._reposModel.rowCount()):
                path = convert_string(self._reposModel.item(row, self.PATH_COLUMN).data(Qt.DisplayRole).toString())
                active = self._reposModel.item(row, self.ACTIVE_COLUMN).checkState == Qt.Checked
                autoUpdate = self._reposModel.item(row, self.AUTO_UPDATE_COLUMN).checkState == Qt.Checked
                repos.append((path, active, autoUpdate))
                
            get_settings().get_plugin_repositories().setExternalRepositories(repos)
            self._modified = False
    
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    w = plugin_repositories()
    w.run_options_widget()
