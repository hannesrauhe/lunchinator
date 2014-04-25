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
            rev = self.getGitCommantOutput(["rev-parse", tags.split("\n")[0]], path=path)
            out = self.getGitCommantOutput(["cat-file", "-p", rev], path=path)
            return out.split("\n")[5:]
        except:
            return None
        
    
    def canGitUpdate(self, ensureMaster=False, path=None):
        if self._gitHandler.getGitCommandResult(["rev-parse"], path) != 0:
            return (False, "'%s' is no git repository" % path)
         
        if self._gitHandler.getGitCommandResult(["diff", "--name-only", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unstaged changes")
         
        if self._gitHandler.getGitCommandResult(["diff", "--cached", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are staged, uncommitted changes")
         
        if ensureMaster:
            _, branch, __ = self._gitHandler.runGitCommand(["symbolic-ref", "HEAD"], path, quiet=False)
            if not branch.endswith("/master"):
                return (False, "The selected branch is not the master branch")
        
        # get upstream branch
        ref = self.getGitCommantOutput(["symbolic-ref", "-q", "HEAD"], path)
        upstream = self.getGitCommantOutput(["for-each-ref", "--format='%(upstream:short)'", ref])
        if self._gitHandler.getGitCommandResult(["log", "%s..HEAD" % upstream, "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unpushed commits on the branch")
        
        return (True, None)

    def needsPull(self, path):
        canUpdate, _reason = self.canGitUpdate(False, path)
        if not canUpdate:
            return False
        
        # update remotes
        if self.getGitCommandResult(["remote", "update"], path) != 0:
            return False
        
        local = self.getGitCommantOutput(["rev-parse", "@"])
        remote = self.getGitCommantOutput(["rev-parse", "@{u}"])
        base = self.getGitCommantOutput(["merge-base", "@", "@{u}"])
        
        if local == remote:
            # up-to-date
            return False
        if local == base:
            # can fast-forward
            return True
        
        # need to push or diverged
        return False
