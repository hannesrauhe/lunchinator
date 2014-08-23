import subprocess
import os

class GitHandler(object):
    UP_TO_DATE_REASON = "Repository is up-to-date"
    
    def __init__(self, logger):
        self._logger = logger
    
    def runGitCommand(self, args, path=None, quiet=True, isStaticCommand=False):
        """Runs a git command and returns a triple (return code, stdout output, stderr output)"""
        if path is None and not isStaticCommand:
            from lunchinator import get_settings
            path = get_settings().get_main_package_path()
         
        if not isStaticCommand:
            call = ["git", "--no-pager", "--git-dir=" + path + "/.git", "--work-tree=" + path]
        else:
            call = ["git", "--no-pager"]
            
        call = call + args
         
        fh = subprocess.PIPE    
        if quiet:
            fh = open(os.path.devnull, "w")
        self._logger.debug("Git call %s", call)
        p = subprocess.Popen(call, stdout=fh, stderr=fh)
        pOut, pErr = p.communicate()
        retCode = p.returncode
        return retCode, pOut, pErr

    def getGitCommandResult(self, args, path=None, quiet=True, isStaticCommand=False):
        """Runs a git command and returns the return code."""
        retCode, _, __ = self.runGitCommand(args, path, quiet, isStaticCommand)
        return retCode
    
    def getGitCommandOutput(self, args, path=None, isStaticCommand=False):
        """Runs a git command and returns the stdout output."""
        _retCode, pOut, _pErr = self.runGitCommand(args, path, quiet=False, isStaticCommand=isStaticCommand)
        return pOut.strip()
    
    def hasGit(self, path=None):
        """Checks if a path is a git repository.
        
        This method returns true iff git is available and the path is
        a git repository. If git is not available, None is returned.
        """
        try:
            return self.getGitCommandResult(["rev-parse"], path=path) == 0
        except:
            # seems git is not available
            return None
        
    def isGitURL(self, url):
        return self.getGitCommandResult(["ls-remote", url], isStaticCommand=True) == 0

    def getCommitCount(self, path=None):
        """Returns the number of commits in the HEAD state of a git repository."""
        try:
            return self.getGitCommandOutput(["rev-list", "--count", "HEAD"], path=path)
        except:
            return None
        
    def getRemoteCommitCount(self, path=None):
        """Returns the number of commits in the current upstream branch of a git repository."""
        try:
            return self.getGitCommandOutput(["rev-list", "--count", "@{u}"], path=path)
        except:
            return None
    
    def canGitUpdate(self, ensureMaster=False, path=None):
        """Checks if a git pull is possible in a git repository.
        
        This method returns True iff:
        - The directory is a git repository, and
        - the git repository is clean and up-to-date with the upstream branch.
        ensureMaster -- If True, this method will also ensure that the
                        current branch is the master branch.
        """
        if self.getGitCommandResult(["rev-parse"], path) != 0:
            return (False, "'%s' is no git repository" % path)
         
        if self.getGitCommandOutput(["rev-parse", "--abbrev-ref", "HEAD"], path) == "HEAD":
            return (False, "Repository is in a detached state")
         
        if self.getGitCommandResult(["diff", "--name-only", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unstaged changes")
         
        if self.getGitCommandResult(["diff", "--cached", "--exit-code", "--quiet"], path) != 0:
            return (False, "There are staged, uncommitted changes")
         
        if ensureMaster:
            _, branch, __ = self.runGitCommand(["symbolic-ref", "HEAD"], path, quiet=False)
            if not branch.endswith("/master"):
                return (False, "The selected branch is not the master branch")
        
        # get upstream branch
        ref = self.getGitCommandOutput(["symbolic-ref", "-q", "HEAD"], path)
        upstream = self.getGitCommandOutput(["for-each-ref", "--format=%(upstream:short)", ref])
        if self.getGitCommandResult(["log", "%s..HEAD" % upstream, "--exit-code", "--quiet"], path) != 0:
            return (False, "There are unpushed commits on the branch")
        
        return (True, None)

    def needsPull(self, returnReason=False, path=None):
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
        
        canUpdate, reason = self.canGitUpdate(False, path)
        if not canUpdate:
            self._logger.debug("Repository %s cannot be updated: %s", path, reason)
            return False if not returnReason else (False, reason)
        
        # update remotes
        if self.getGitCommandResult(["remote", "update"], path) != 0:
            return False if not returnReason else (False, "Error updating repository")
        
        local = self.getGitCommandOutput(["rev-parse", "HEAD"], path)
        remote = self.getGitCommandOutput(["rev-parse", "@{u}"], path)
        base = self.getGitCommandOutput(["merge-base", "HEAD", "@{u}"], path)
        
        if local == remote:
            # up-to-date
            self._logger.debug("Repository %s up-to-date", path)
            return False if not returnReason else (False, self.UP_TO_DATE_REASON)
        if local == base:
            # can fast-forward
            return True if not returnReason else (True, None)
        
        # need to push or diverged
        self._logger.debug("Repository %s needs to be pushed or is diverged", path)
        return False if not returnReason else (False, "Repository contains unpushed commits or is diverged")
    
    def pull(self, path=None):
        """Pulls a git repository. Does not check prerequisites!"""
        return self.runGitCommand(["pull"], path)
    
    def extractRepositoryNameFromURL(self, url):
        if url.endswith(u"/.git"):
            url = url[:-5]
        elif url.endswith(u".git"):
            url = url[:-4]
        try:
            firstChar = url.rfind(u"/") + 1
        except IndexError:
            firstChar = 0
        url = url[firstChar:]
        if u":" in url:
            url = url[url.index(u":") + 1:]
        return url
        
    def clone(self, url, targetDir):
        return self.getGitCommandResult(["clone", url, targetDir], isStaticCommand=True)
        
