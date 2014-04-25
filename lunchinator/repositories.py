from threading import Lock
from copy import deepcopy
from git import GitHandler

class PluginRepositories(object):
    def __init__(self, internalDir, externalRepos):
        self._internalDir = internalDir
        self._externalRepos = externalRepos
        self._lock = Lock()
        
    def getPluginDirs(self):
        with self._lock:
            return [self._internalDir] + [tup[0] for tup in self._externalRepos]
    
    def getExternalRepositories(self):
        return self._externalRepos
    
    def setExternalRepositories(self, repos):
        with self._lock:
            self._externalRepos = repos

    def checkForUpdates(self):
        """
        Checks each repository for updates and returns a list of paths
        where updates are available.
        """
        with self._lock:
            # make a copy s.t. we don't have to lock the repos all the time
            repos = deepcopy(self._externalRepos)
            
        outdated = []
        gitHandler = GitHandler()
        for path, _active, autoUpdate in repos:
            if autoUpdate and gitHandler.needsPull(path):
                outdated.append(path)
                
        return outdated
                    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
    