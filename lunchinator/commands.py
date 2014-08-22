import json
import subprocess
from lunchinator.git import GitHandler
from lunchinator.log import getLogger

class Commands(object):
    """Convenience class that encapsules and handles execution of multiple commands."""
    _SHELL_COMMAND = "sh"
    _GIT_PULL = "gp"
    
    def __init__(self, stringRep=None):
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
        getLogger().info("Executing: %s", ' '.join(args))
        try:
            subprocess.call(args)
        except:
            getLogger().exception("Error executing command.")
    
    def _do_gp(self, path):
        getLogger().info("Pulling git repository: %s", path)
        retCode, _pOut, pErr = GitHandler.pull(path)
        if retCode != 0:
            if pErr:
                getLogger().error(u"Error pulling git repository. Stderr: %s", pErr.decode("utf-8"))
            else:
                getLogger().error("Error pulling git repository.")
