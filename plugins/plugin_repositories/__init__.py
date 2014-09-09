from lunchinator import convert_string, get_notification_center, get_settings
from lunchinator.plugin import iface_general_plugin
from lunchinator.utilities import getValidQtParent
from lunchinator.git import GitHandler
from lunchinator.log.logging_func import loggingFunc
import os
from functools import partial
    
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
        
    def get_displayed_name(self):
        return u"Plugin Repositories"
        
    def activate(self):
        iface_general_plugin.activate(self)
        get_notification_center().connectOutdatedRepositoriesChanged(self._processUpdates)
        get_notification_center().connectUpToDateRepositoriesChanged(self._processUpdates)
        
    def deactivate(self):
        get_notification_center().disconnectOutdatedRepositoriesChanged(self._processUpdates)
        get_notification_center().disconnectUpToDateRepositoriesChanged(self._processUpdates)
        iface_general_plugin.deactivate(self)
        
    def has_options_widget(self):
        return True
        
    def create_options_widget(self, parent):
        from plugin_repositories.plugin_repositories_gui import PluginRepositoriesGUI
        self._ui = PluginRepositoriesGUI(self.logger, parent)
        
        self._initRepositories()
        self._ui.resizeColumns()
        
        self._ui.getTable().model().itemChanged.connect(self._itemChanged)
        self._ui.getTable().model().rowsRemoved.connect(self._rowsRemoved)
        self._ui.addRepository.connect(self._addRepository)
        self._ui.checkForUpdates.connect(self._checkForUpdates)
        
        if self._statusHolder != None:
            self._setStatus(self._statusHolder, self._progressHolder)
        
        return self._ui  
    
    def _needsRestart(self):
        self._restartRequired = True
    
    @loggingFunc
    def _addRepository(self):
        from plugin_repositories.add_repo_dialog import AddRepoDialog
        dialog = AddRepoDialog(self._ui, self.logger)
        dialog.exec_()
        if dialog.result() == AddRepoDialog.Accepted:
            self._ui.appendRepository(dialog.getPath(),
                                   dialog.isRepositoryActive(),
                                   dialog.isAutoUpdateEnabled(),
                                   dialog.canAutoUpdate())
            self._needsRestart()
            self._modified = True
    
    @loggingFunc
    def _itemChanged(self, _item):
        self._modified = True
        
    @loggingFunc
    def _rowsRemoved(self, _parent, _start, _end):
        self._modified = True
        self._needsRestart()
    
    def _initRepositories(self):
        self._modified = False
        self._ui.clear()
        for path, active, auto_update in get_settings().get_plugin_repositories().getExternalRepositories():
            if os.path.isdir(path):
                self._ui.appendRepository(path, active, auto_update)
        
    @loggingFunc
    def _processUpdates(self, aTuple=None):
        if self._ui != None:
            if aTuple:
                outdated, upToDate = aTuple
            else:
                outdated = None
                upToDate = None
            self._ui.updateStatusItems(outdated, upToDate)
            self._setStatus(None)
        
    @loggingFunc
    def _checkForUpdates(self):
        if self._ui.getTable().model().rowCount() == 0:
            return
        
        from lunchinator.callables import AsyncCall
        self._setStatus("Checking for updates...", True)
        AsyncCall(getValidQtParent(),
                  self.logger,
                  self._checkAllRepositories,
                  self._processUpdates,
                  self._checkingError)()
        
    def _checkAllRepositories(self):
        from PyQt4.QtCore import Qt
        from plugin_repositories.plugin_repositories_gui import PluginRepositoriesGUI
        model = self._ui.getTable().model()
        outdated = set()
        upToDate = {}
        gh = GitHandler(self.logger)
        for row in xrange(model.rowCount()):
            path = convert_string(model.item(row, PluginRepositoriesGUI.PATH_COLUMN).data(Qt.DisplayRole).toString())
            if gh.hasGit(path):
                needsPull, reason = gh.needsPull(True, path)
                if needsPull:
                    outdated.add(path)
                else:
                    upToDate[path] = reason
        return outdated, upToDate

    @loggingFunc
    def _checkingError(self, msg):
        self._setStatus("Error: " + msg)
        
    def _setStatus(self, msg, progress=False):
        if self._ui != None:
            self._ui.setStatus(msg, progress)
        else:
            self._statusHolder = msg
            self._progressHolder = progress
        
    def discard_changes(self):
        self._initRepositories()
        if self._ui is not None:
            self._ui.resizeColumns()
        
    def save_options_widget_data(self, **_kwargs):
        if self._modified:
            from PyQt4.QtCore import Qt
            from plugin_repositories.plugin_repositories_gui import PluginRepositoriesGUI
            repos = []
            model = self._ui.getTable().model() 
            for row in xrange(model.rowCount()):
                path = convert_string(model.item(row, PluginRepositoriesGUI.PATH_COLUMN).data(Qt.DisplayRole).toString())
                active = model.item(row, PluginRepositoriesGUI.ACTIVE_COLUMN).checkState() == Qt.Checked
                autoUpdate = model.item(row, PluginRepositoriesGUI.AUTO_UPDATE_COLUMN).checkState() == Qt.Checked
                repos.append((path, active, autoUpdate))
                
            activeChanged = get_settings().get_plugin_repositories().setExternalRepositories(repos)
            self._modified = False
            if self._restartRequired or activeChanged:
                self._restartRequired = False
                get_notification_center().emitRestartRequired(u"Plugin Repositories have been modified.")
    
if __name__ == '__main__':
    from lunchinator.plugin import iface_gui_plugin
    w = plugin_repositories()
    w.run_options_widget()
