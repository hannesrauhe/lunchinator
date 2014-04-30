from threading import Lock
from copy import deepcopy
from git import GitHandler
from lunchinator import get_notification_center

class PluginRepositories(object):
    def __init__(self, internalDir, externalRepos):
        self._internalDir = internalDir
        self._externalRepos = externalRepos
        self._outdated = set()
        self._upToDate = set()
        self._lock = Lock()
        
    def getPluginDirs(self):
        with self._lock:
            return [self._internalDir] + [tup[0] for tup in self._externalRepos]
    
    def getExternalRepositories(self):
        return self._externalRepos
    
    def setExternalRepositories(self, repos):
        with self._lock:
            self._externalRepos = repos

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
            get_notification_center().emitRepositoryUpdate(outdated)
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
    