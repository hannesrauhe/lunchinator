import json
import subprocess
from lunchinator.git import GitHandler

class Commands(object):
    """Convenience class that encapsules and handles execution of multiple commands."""
    _SHELL_COMMAND = "sh"
    _GIT_PULL = "gp"
    
    def __init__(self, logger, stringRep=None):
        self._logger = logger
        if stringRep:
            self._cmds = self._fromString(stringRep)
        else:
            self._cmds = []
        
    def addShellCommand(self, args):
        """Adds a list of arguments that will be passed to subprocess."""
        self._cmds.append((self._SHELL_COMMAND, args))
        
    def addGitPull(self, path):
        """Adds a git pull command for a given path."""
        self._cmds.append((self._GIT_PULL, path))
        
    def toString(self):
        """generates a string representation that can later be passed to the constructor."""
        return json.dumps(self._cmds)
    
    def _fromString(self, s):
        return json.loads(s)
        
    def executeCommands(self):
        """Executes the commands in the order they were added."""
        for cmd in self._cmds:
            method = "_do_" + cmd[0]
            
            if hasattr(self, method): 
                _member = getattr(self, method)
                _member(cmd[1])
                
    def _do_sh(self, args):
        self._logger.info("Executing: %s", ' '.join(args))
        try:
            subprocess.call(args)
        except:
            self._logger.exception("Error executing command.")
    
    def _do_gp(self, path):
        self._logger.info("Pulling git repository: %s", path)
        gitHandler = GitHandler(self._logger)
        retCode, _pOut, pErr = gitHandler.pull(path)
        if retCode != 0:
            if pErr:
                self._logger.error(u"Error pulling git repository. Stderr: %s", pErr.decode("utf-8"))
            else:
                self._logger.error("Error pulling git repository.")
