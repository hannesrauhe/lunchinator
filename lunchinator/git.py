import subprocess
import os

class GitHandler(object):
    def runGitCommand(self, args, path=None, quiet=True):
        if path == None:
            from lunchinator import get_settings
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
    
    def getGitCommantOutput(self, args, path=None):
        _retCode, pOut, _pErr = self.runGitCommand(args, path, quiet=False)
        return pOut.strip()
    
    def has_git(self, path=None):
        try:
            return self.getGitCommandResult(["rev-parse"], path=path) == 0
        except:
            return None

    def getCommitCount(self, path=None):
        try:
            return self.getGitCommantOutput(["rev-list", "--count", "HEAD"], path=path)
        except:
            return None

    def getLatestChangeLog(self, path=None):
        try:
            tags = self.getGitCommantOutput(["tag"], path=path)
            rev = self.getGitCommantOutput(["rev-parse", tags.split("\n")[-1]], path=path)
            out = self.getGitCommantOutput(["cat-file", "-p", rev], path=path)
            return out.split("\n")[5:]
        except:
            return None
