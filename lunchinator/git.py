import subprocess
import os
from lunchinator import log_debug, log_warning, log_exception

class GitHandler(object):
    UP_TO_DATE_REASON = "Repository is up-to-date"
    
    @classmethod
    def runGitCommand(cls, args, path=None, quiet=True):
        """Runs a git command and returns a triple (return code, stdout output, stderr output)"""
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
        """Runs a git command and returns the return code."""
        retCode, _, __ = cls.runGitCommand(args, path, quiet)
        return retCode
    
    @classmethod
    def getGitCommandOutput(cls, args, path=None):
        """Runs a git command and returns the stdout output."""
        _retCode, pOut, _pErr = cls.runGitCommand(args, path, quiet=False)
        return pOut.strip()
    
    @classmethod
    def hasGit(cls, path=None):
        """Checks if a path is a git repository.
        
        This method returns true iff git is available and the path is
        a git repository. If git is not available, None is returned.
        """
        try:
            return cls.getGitCommandResult(["rev-parse"], path=path) == 0
        except:
            # seems git is not available
            return None

    @classmethod
    def getCommitCount(cls, path=None):
        """Returns the number of commits in the HEAD state of a git repository."""
        try:
            return cls.getGitCommandOutput(["rev-list", "--count", "HEAD"], path=path)
        except:
            return None
        
    @classmethod
    def getRemoteCommitCount(cls, path=None):
        """Returns the number of commits in the current upstream branch of a git repository."""
        try:
            return cls.getGitCommandOutput(["rev-list", "--count", "@{u}"], path=path)
        except:
            return None
    
    @classmethod
    def canGitUpdate(cls, ensureMaster=False, path=None):
        """Checks if a git pull is possible in a git repository.
        
        This method returns True iff:
        - The directory is a git repository, and
        - the git repository is clean and up-to-date with the upstream branch.
        ensureMaster -- If True, this method will also ensure that the
                        current branch is the master branch.
        """
        if cls.getGitCommandResult(["rev-parse"], path) != 0:
            return (False, "'%s' is no git repository" % path)
         
        if cls.getGitCommandOutput(["rev-parse", "--abbrev-ref", "HEAD"], path) == "HEAD":
            return (False, "Repository is in a detached state")
         
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
    def needsPull(cls, returnReason=False, path=None):
        """Checks if a git repository is outdated and can be pulled.
        
        This method will return True iff
        - git updates are possible (see canGitUpdate)
        - the upstream branch contains commits that can be pulled.
        returnReason -- If True, this method returns a tuple (needsPull, reasonString)
                        where reasonString contains the reason why the
                        repository does NOT need to be pulled or is None
                        if it can be pulled.
        """
        if path == None:
            from lunchinator import get_settings
            path = get_settings().get_main_package_path()
        
        canUpdate, reason = cls.canGitUpdate(False, path)
        if not canUpdate:
            log_debug("Repository", path, "cannot be updated:", reason)
            return False if not returnReason else (False, reason)
        
        # update remotes
        if cls.getGitCommandResult(["remote", "update"], path) != 0:
            return False if not returnReason else (False, "Error updating repository")
        
        local = cls.getGitCommandOutput(["rev-parse", "HEAD"], path)
        remote = cls.getGitCommandOutput(["rev-parse", "@{u}"], path)
        base = cls.getGitCommandOutput(["merge-base", "HEAD", "@{u}"], path)
        
        if local == remote:
            # up-to-date
            log_debug("Repository", path, "up-to-date")
            return False if not returnReason else (False, cls.UP_TO_DATE_REASON)
        if local == base:
            # can fast-forward
            return True if not returnReason else (True, None)
        
        # need to push or diverged
        log_debug("Repository", path, "needs to be pushed or is diverged")
        return False if not returnReason else (False, "Repository contains unpushed commits or is diverged")
    
    @classmethod
    def pull(cls, path=None):
        """Pulls a git repository. Does not check prerequisites!"""
        return cls.runGitCommand(["pull"], path)
