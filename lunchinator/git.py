from lunchinator import get_settings
import subprocess
import os

class GitHandler(object):
    def runGitCommand(self, args, path=None, quiet=True):
        if path == None:
            path = get_settings().get_main_package_path()
         
        call = ["git", "--no-pager", "--git-dir=" + path + "/.git", "--work-tree=" + path]
        call = call + args
         
        fh = subprocess.PIPE    
        if quiet:
            fh = open(os.path.devnull, "w")
        p = subprocess.Popen(call, stdout=fh, stderr=fh)
        pOut, pErr = p.communicate()
        retCode = p.returncode
        return retCode, pOut, pErr
    
    def getGitCommandResult(self, args, path=None, quiet=True):
        retCode, _, __ = self.runGitCommand(args, path, quiet)
        return retCode
    
    def has_git(self):
        try:
            return self.getGitCommandResult(["rev-parse"]) == 0
        except:
            return None
