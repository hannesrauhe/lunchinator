from threading import Lock

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
    
    def __enter__(self):
        return self._lock.__enter__()
    
    def __exit__(self, aType, value, traceback):
        return self._lock.__exit__(aType, value, traceback)
