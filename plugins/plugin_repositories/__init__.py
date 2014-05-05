import os
from functools import partial
from lunchinator import convert_string, get_notification_center, get_settings
from lunchinator.iface_plugins import iface_general_plugin
from lunchinator.utilities import getValidQtParent
from lunchinator.git import GitHandler
from lunchinator.callables import AsyncCall
from plugin_repositories.plugin_repositories_gui import PluginRepositoriesGUI
    
class plugin_repositories(iface_general_plugin):
    def __init__(self):
        super(plugin_repositories, self).__init__()
        self._ui = None
        self._modified = False
        self._statusHolder = None
        self._progressHolder = False
        self.force_activation = True
        self._restartRequired = False
        self._outdated = set()
        self._upToDate = set()
        
    def activate(self):
        iface_general_plugin.activate(self)
        get_notification_center().connectOutdatedRepositoriesChanged(self._processUpdates)
        get_notification_center().connectUpToDateRepositoriesChanged(self._processUpdates)
        
    def deactivate(self):
        get_notification_center().disconnectOutdatedRepositoriesChanged(self._processUpdates)
        get_notification_center().disconnectUpToDateRepositoriesChanged(self._processUpdates)
        iface_general_plugin.deactivate(self)
        
    def create_options_widget(self, parent):
        self._ui = PluginRepositoriesGUI(parent)
        
        self._initRepositories()
        self._ui.resizeColumns()
        
        self._ui.getTable().model().itemChanged.connect(self._itemChanged)
        self._ui.getTable().model().rowsRemoved.connect(self._rowsRemoved)
        self._ui.addRepository.connect(self._addRepository)
        self._ui.checkForUpdates.connect(self._checkForUpdates)
        
        if self._statusHolder:
            self._setStatus(self._statusHolder, self._progressHolder)
        
        return self._ui  
    
    def _needsRestart(self):
        self._restartRequired = True
    
    def _addRepository(self):
        from plugin_repositories.add_repo_dialog import AddRepoDialog
        dialog = AddRepoDialog(self._ui)
        dialog.exec_()
        if dialog.result() == AddRepoDialog.Accepted:
            self._ui.appendRepository(dialog.getPath(),
                                   dialog.isRepositoryActive(),
                                   dialog.isAutoUpdateEnabled(),
                                   dialog.canAutoUpdate())
            self._needsRestart()
            self._modified = True
    
    def _itemChanged(self, _item):
        self._modified = True
        
    def _rowsRemoved(self, _parent, _start, _end):
        self._modified = True
        self._needsRestart()
    
    def _initRepositories(self):
        self._modified = False
        self._ui.clear()
        for path, active, auto_update in get_settings().get_plugin_repositories().getExternalRepositories():
            if os.path.isdir(path):
                self._ui.appendRepository(path, active, auto_update)
        
    def _processUpdates(self, aTuple=None):
        if self._ui != None:
            if aTuple:
                outdated, upToDate = aTuple
            else:
                outdated = None
                upToDate = None
            self._ui.updateStatusItems(outdated, upToDate)
            self._setStatus(None)
        
    def _checkForUpdates(self):
        if self._ui.getTable().model().rowCount() == 0:
            return
        
        self._setStatus("Checking for updates...", True)
        AsyncCall(getValidQtParent(),
                  self._checkAllRepositories,
                  self._processUpdates,
                  self._checkingError)()
        
    def _checkAllRepositories(self):
        from PyQt4.QtCore import Qt
        model = self._ui.getTable().model()
        outdated = set()
        upToDate = set()
        for row in xrange(model.rowCount()):
            path = convert_string(model.item(row, PluginRepositoriesGUI.PATH_COLUMN).data(Qt.DisplayRole).toString())
            if GitHandler.hasGit(path):
                if GitHandler.needsPull(path=path):
                    outdated.add(path)
                else:
                    upToDate.add(path)
        return outdated, upToDate

    def _checkingError(self, msg):
        self._setStatus("Error: " + msg)
        
    def _setStatus(self, msg, progress=False):
        if self._ui:
            self._ui.setStatus(msg, progress)
        else:
            self._statusHolder = msg
            self._progressHolder = progress
        
    def discard_changes(self):
        self._initRepositories()
        
    def save_options_widget_data(self):
        if self._modified:
            from PyQt4.QtCore import Qt
            repos = []
            model = self._ui.getTable().model() 
            for row in xrange(model.rowCount()):
                path = convert_string(model.item(row, PluginRepositoriesGUI.PATH_COLUMN).data(Qt.DisplayRole).toString())
                active = model.item(row, PluginRepositoriesGUI.ACTIVE_COLUMN).checkState() == Qt.Checked
                autoUpdate = model.item(row, PluginRepositoriesGUI.AUTO_UPDATE_COLUMN).checkState() == Qt.Checked
                repos.append((path, active, autoUpdate))
                
            get_settings().get_plugin_repositories().setExternalRepositories(repos)
            self._modified = False
            if self._restartRequired:
                self._restartRequired = False
                get_notification_center().emitRestartRequired(u"Plugin Repositories have been modified.")
    
if __name__ == '__main__':
    from lunchinator.iface_plugins import iface_gui_plugin
    w = plugin_repositories()
    w.run_options_widget()
