from copy import deepcopy
from git import GitHandler
from lunchinator import get_notification_center
from lunchinator.logging_mutex import loggingMutex
from lunchinator.log import loggingFunc

class PluginRepositories(object):
    """Manages external plugin repositories."""
    
    PATH_INDEX = 0
    ACTIVE_INDEX = 1
    AUTO_UPDATE_INDEX = 2
    
    def __init__(self, internalDir, externalRepos, logging=False):
        self._internalDir = internalDir
        self._externalRepos = externalRepos
        self._outdated = set()
        self._upToDate = set()
        self._lock = loggingMutex("repositories", logging=logging)
        
    def getPluginDirs(self, onlyActive=True):
        """Returns a list of directories in which to search for plugins.
        
        The returned list is a copy.
        """
        with self._lock:
            return [self._internalDir] + [tup[self.PATH_INDEX]
                                          for tup in self._externalRepos
                                          if not onlyActive or tup[self.ACTIVE_INDEX]]
    
    def getExternalRepositories(self):
        """Returns the internal data structure holding the plugin repository information.
        
        This method is used by lunch_settings and the plugin_repositories plugin.
        """
        return self._externalRepos
    
    def setExternalRepositories(self, repos):
        """Sets the list of external plugin repositories.
        
        This method is used by lunch_settings and the plugin_repositories plugin.
        """
        with self._lock:
            activeChanged = False # did any repository change its active state
            outDatedChanged = False
            upToDateChanged = False
            allRepos = set()
            for newRepo in repos:
                allRepos.add(newRepo)
                if not newRepo[self.AUTO_UPDATE_INDEX] and self._isAutoUpdateEnabled(newRepo[self.PATH_INDEX]):
                    # don't want to auto update this repo any more
                    if self._isOutdated(newRepo[self.PATH_INDEX]):
                        outDatedChanged = True
                        self._outdated.remove(newRepo[self.PATH_INDEX])
                    if self._isUpToDate(newRepo[self.PATH_INDEX]):
                        upToDateChanged = True
                        self._upToDate.remove(newRepo[self.PATH_INDEX])
            
                oldActiveState = self._isActive(newRepo[self.PATH_INDEX])
                if oldActiveState != None and oldActiveState != newRepo[self.ACTIVE_INDEX]:
                    activeChanged = True
            
            # check for removed repos
            removedOutdated = self._outdated - allRepos
            if removedOutdated:
                outDatedChanged = True
                self._outdated -= removedOutdated
            removedUpToDate = self._upToDate - allRepos
            if removedUpToDate:
                upToDateChanged = True
                self._upToDate -= removedUpToDate
                
            self._externalRepos = repos
        if outDatedChanged:
            get_notification_center().emitOutdatedRepositoriesChanged()
        if upToDateChanged:
            get_notification_center().emitUpToDateRepositoriesChanged()
        get_notification_center().emitRepositoriesChanged()
        
        return activeChanged

    @loggingFunc
    def checkForUpdates(self, forced=False):
        """Checks each repository for updates.
        
        Returns a set of paths where updates are available.
        forced -- If True, repositories with autoUpdate==False are checked, too.
        """
        with self._lock:
            # make a copy s.t. we don't have to lock the repos all the time
            repos = deepcopy(self._externalRepos)
            
        outdated = set()
        upToDate = set()
        for path, _active, autoUpdate in repos:
            if forced or autoUpdate:
                if GitHandler.needsPull(path=path):
                    outdated.add(path)
                else:
                    upToDate.add(path)
                
        with self._lock:
            self._outdated -= upToDate
            self._outdated.update(outdated)
            
            self._upToDate -= outdated
            self._upToDate.update(upToDate)
            
        if outdated:
            get_notification_center().emitOutdatedRepositoriesChanged()
        if upToDate:
            get_notification_center().emitUpToDateRepositoriesChanged()
        return outdated

    def areUpdatesAvailable(self):
        """Returns True if there are outdated repositories."""
        return len(self._outdated) > 0
    
    def getOutdated(self):
        """Returns the set of outdated repositories.
        
        The returned set is a copy.
        """
        with self._lock:
            return set(self._outdated)
        
    def getNumOutdated(self):
        """Returns the number of outdated repositories."""
        with self._lock:
            return len(self._outdated)
    
    def getUpToDate(self):
        """Returns the set of up-to-date repositories.
        
        The returned set is a copy.
        """
        with self._lock:
            return set(self._upToDate)
    
    def _isOutdated(self, path):
        return path in self._outdated
    
    def _isUpToDate(self, path):
        return path in self._upToDate
    
    def isOutdated(self, path):
        """Returns True if the given repository is outdated."""
        with self._lock:
            return self._isOutdated(path)
    
    def isUpToDate(self, path):
        """Returns True if the given repository is up-to-date."""
        with self._lock:
            return self._isUpToDate(path)
    
    def _isAutoUpdateEnabled(self, path):
        """Returns True if auto update is enabled for the given repository."""
        for repo in self.getExternalRepositories():
            if repo[self.PATH_INDEX] == path:
                return repo[self.AUTO_UPDATE_INDEX]
        return False
       
    def _isActive(self, path):
        """Returns True if auto update is enabled for the given repository."""
        for repo in self.getExternalRepositories():
            if repo[self.PATH_INDEX] == path:
                return repo[self.ACTIVE_INDEX]
        return None
    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
