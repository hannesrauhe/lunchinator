from lunchinator import get_server, log_warning, convert_string
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
    
class plugin_repositories(iface_general_plugin):
    CHECK_INTERVAL = 12 * 60 * 60 * 1000 # check twice a day
    PATH_COLUMN = 1
    ACTIVE_COLUMN = 0
    AUTO_UPDATE_COLUMN = 2
    
    def __init__(self):
        super(plugin_repositories, self).__init__()
        self._modified = False
    
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QStandardItemModel, QStandardItem, QWidget, \
                                QVBoxLayout, QLabel, QSizePolicy, QPushButton, \
                                QTextEdit, QProgressBar, QStackedWidget, QTreeView, \
                                QStandardItemModel
        from PyQt4.QtCore import Qt
       
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self._reposTable = QTreeView(widget) 
        self._reposTable.setIndentation(0)
        
        self._reposModel = QStandardItemModel(self._reposTable)
        self._initModel()
        self._reposTable.setModel(self._reposModel)
        
        layout.addWidget(self._reposTable)
        
        addButton = QPushButton("Add Repository...")
        addButton.clicked.connect(partial(self._addRepository, widget))
        layout.addWidget(addButton)
        
        self._initRepositories()
        
        self._reposTable.resizeColumnToContents(self.ACTIVE_COLUMN)
        self._reposTable.resizeColumnToContents(self.AUTO_UPDATE_COLUMN)
        self._reposTable.setColumnWidth(self.PATH_COLUMN, 150)
        return widget  
    
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
        stringList = QStringList([u"Active", u"Path", u"Auto Update"])
        self._reposModel.setColumnCount(stringList.count())
        self._reposModel.setHorizontalHeaderLabels(stringList)
    
    def _initRepositories(self):
        self._modified = False
        self._initModel()
        for path, active, auto_update in get_settings().get_plugin_repositories().getExternalRepositories():
            if os.path.isdir(path):
                self._appendRepository(path, active, auto_update)
             
    def _appendRepository(self, path, active, autoUpdate, canAutoUpdate = None):
        from PyQt4.QtGui import QStandardItem
        from PyQt4.QtCore import Qt, QSize

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
                
        self._reposModel.appendRow([activeItem, pathItem, autoUpdateItem])
        
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
