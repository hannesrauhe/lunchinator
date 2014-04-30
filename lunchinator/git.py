import subprocess
import os
from lunchinator import log_debug

class GitHandler(object):
    @classmethod
    def runGitCommand(cls, args, path=None, quiet=True):
        if path == None:
            from lunchinator import get_settings
            path = get_settings().get_main_package_path()
         
        call = ["git", "--no-pager", "--git-dir=" + path + "/.git", "--work-tree=" + path]
        call = call + args
         
        fh = subprocess.PIPE    
        if quiet:
            fh = open(os.path.devnull, "w")
        log_debug("Git call", call)
        p = subprocess.Popen(call, stdout=fh, stderr=fh)
        pOut, pErr = p.communicate()
        retCode = p.returncode
        return retCode, pOut, pErr
    
    @classmethod
    def getGitCommandResult(cls, args, path=None, quiet=True):
        retCode, _, __ = cls.runGitCommand(args, path, quiet)
        return retCode
    
    @classmethod
    def getGitCommandOutput(cls, args, path=None):
        _retCode, pOut, _pErr = cls.runGitCommand(args, path, quiet=False)
        return pOut.strip()
    
    @classmethod
    def hasGit(cls, path=None):
        try:
            return cls.getGitCommandResult(["rev-parse"], path=path) == 0
        except:
            return None

    @classmethod
    def getCommitCount(cls, path=None):
        try:
            return cls.getGitCommandOutput(["rev-list", "--count", "HEAD"], path=path)
        except:
            return None
        
    @classmethod
    def getRemoteCommitCount(cls, path=None):
        try:
            return cls.getGitCommandOutput(["rev-list", "--count", "@{u}"], path=path)
        except:
            return None

    @classmethod
    def getLatestChangeLog(cls, path=None):
        try:
            tags = cls.getGitCommandOutput(["tag"], path=path)
            rev = cls.getGitCommandOutput(["rev-parse", tags.split("\n")[-1]], path=path)
            out = cls.getGitCommandOutput(["cat-file", "-p", rev], path=path)
            return out.split("\n")[5:]
        except:
            return None
    
    @classmethod
    def canGitUpdate(cls, ensureMaster=False, path=None):
        if cls.getGitCommandResult(["rev-parse"], path) != 0:
            return (False, "'%s' is no git repository" % path)
         
        if cls.getGitCommandResult(["diff", "--name-only", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unstaged changes")
         
        if cls.getGitCommandResult(["diff", "--cached", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are staged, uncommitted changes")
         
        if ensureMaster:
            _, branch, __ = cls.runGitCommand(["symbolic-ref", "HEAD"], path, quiet=False)
            if not branch.endswith("/master"):
                return (False, "The selected branch is not the master branch")
        
        # get upstream branch
        ref = cls.getGitCommandOutput(["symbolic-ref", "-q", "HEAD"], path)
        upstream = cls.getGitCommandOutput(["for-each-ref", "--format=%(upstream:short)", ref])
        if cls.getGitCommandResult(["log", "%s..HEAD" % upstream, "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unpushed commits on the branch")
        
        return (True, None)

    @classmethod
    def needsPull(cls, path=None, returnReason=False):
        if path == None:
            from lunchinator import get_settings
            path = get_settings().get_main_package_path()
        
        canUpdate, reason = cls.canGitUpdate(False, path)
        if not canUpdate:
            log_debug("Repository", path, "cannot be updated:", reason)
            return False if not returnReason else (False, reason)
        
        # update remotes
        if cls.getGitCommandResult(["remote", "update"], path) != 0:
            return False if not returnReason else (False, "Error updating repository.")
        
        local = cls.getGitCommandOutput(["rev-parse", "HEAD"], path)
        remote = cls.getGitCommandOutput(["rev-parse", "@{u}"], path)
        base = cls.getGitCommandOutput(["merge-base", "HEAD", "@{u}"], path)
        
        if local == remote:
            # up-to-date
            log_debug("Repository", path, "up-to-date")
            return False if not returnReason else (False, "Repository is up-to-date.")
        if local == base:
            # can fast-forward
            return True if not returnReason else (True, None)
        
        # need to push or diverged
        log_debug("Repository", path, "needs to be pushed or is diverged")
        return False if not returnReason else (False, "Repository contains unpushed commits or is diverged.")
    
    @classmethod
    def pull(cls, path=None):
        cls.runGitCommand(["pull"], path)
    