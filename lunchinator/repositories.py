from threading import Lock
from copy import deepcopy
from git import GitHandler
from lunchinator import get_notification_center

class PluginRepositories(object):
    PATH_INDEX = 0
    ACTIVE_INDEX = 1
    AUTO_UPDATE_INDEX = 2
    
    def __init__(self, internalDir, externalRepos):
        self._internalDir = internalDir
        self._externalRepos = externalRepos
        self._outdated = set()
        self._upToDate = set()
        self._lock = Lock()
        
    def getPluginDirs(self):
        with self._lock:
            return [self._internalDir] + [tup[self.PATH_INDEX] for tup in self._externalRepos]
    
    def getExternalRepositories(self):
        return self._externalRepos
    
    def setExternalRepositories(self, repos):
        with self._lock:
            outDatedChanged = False
            for newRepo in repos:
                if not newRepo[self.AUTO_UPDATE_INDEX] and self.isAutoUpdateEnabled(newRepo[self.PATH_INDEX]):
                    # don't want to auto update this repo any more
                    if self.isOutdated(newRepo[self.PATH_INDEX]):
                        outDatedChanged = True
                        self._outdated.remove(newRepo[self.PATH_INDEX])
                    if self.isUpToDate(newRepo[self.PATH_INDEX]):
                        self._upToDate.remove(newRepo[self.PATH_INDEX])
            self._externalRepos = repos
        if outDatedChanged:
            get_notification_center().emitOutdatedRepositoriesChanged()
        get_notification_center().emitRepositoriesChanged()

    def checkForUpdates(self, forced=False):
        """
        Checks each repository for updates and returns a set of paths
        where updates are available.
        If forced==True, also repositories with autoUpdate==False are checked.
        """
        with self._lock:
            # make a copy s.t. we don't have to lock the repos all the time
            repos = deepcopy(self._externalRepos)
            
        outdated = set()
        upToDate = set()
        for path, _active, autoUpdate in repos:
            if forced or autoUpdate:
                if GitHandler.needsPull(path):
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
        return outdated

    def areUpdatesAvailable(self):
        return len(self._outdated) > 0
    
    def getOutdated(self):
        return self._outdated
    
    def getUpToDate(self):
        return self._upToDate
    
    def isAutoUpdateEnabled(self, path):
        for repo in self.getExternalRepositories():
            if repo[0] == path:
                return repo[2]
        return False
    
    def isOutdated(self, path):
        return path in self._outdated
    
    def isUpToDate(self, path):
        return path in self._upToDate
       
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
    