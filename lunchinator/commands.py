import json
import subprocess
from lunchinator.git import GitHandler

class Commands(object):
    _SHELL_COMMAND = "sh"
    _GIT_PULL = "gp"
    
    def __init__(self, stringRep=None):
        if stringRep:
            self._cmds = self._fromString(stringRep)
        else:
            self._cmds = []
        
    def addShellCommand(self, args):
        self._cmds.append((self._SHELL_COMMAND, args))
        
    def addGitPull(self, path):
        self._cmds.append((self._GIT_PULL, path))
        
    def toString(self):
        return json.dumps(self._cmds)
    
    def _fromString(self, s):
        return json.loads(s)
        
    def _do_sh(self, args):
        subprocess.call(args)
    
    def _do_gp(self, path):
        GitHandler.pull(path)
        
    def executeCommands(self):
        for cmd in self._cmds:
            method = "_do_" + cmd[0]
            
            if hasattr(self, method): 
                _member = getattr(self, method)
                _member(cmd[1])
