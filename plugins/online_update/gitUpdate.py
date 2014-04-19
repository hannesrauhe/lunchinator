from lunchinator import get_settings, get_server, log_info, log_error
from lunchinator.utilities import getPlatform, PLATFORM_WINDOWS
import subprocess, os, shutil, sys

UPDATE_SCRIPT = get_settings().get_resource("bin","updateViaGit.py")
UPDATE_SCRIPT_EXEC_PATH = os.path.join(get_settings().get_main_config_dir(),"updateViaGit.py")

class gitUpdate(object):        
    def create_options_widget(self,parent):
        from PyQt4.QtGui import QStandardItemModel, QStandardItem, QWidget, QVBoxLayout, QLabel, QSizePolicy, QPushButton, QTextEdit, QProgressBar
       
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        versionLabel = QLabel("Installed Version: " + get_settings().get_commit_count())
        layout.addWidget(versionLabel)
        
        #todo: add info about repo (remote url....)
        
        self._statusLabel = QLabel("Lunchinator Updates via Git")
        layout.addWidget(self._statusLabel)
        
        self._checkButton = QPushButton("Check for new Version", parent)
#         self._checkButton.clicked.connect(self.check_for_update)
        
        layout.addWidget(self._checkButton)
        
        self._installButton = QPushButton("Pull and Restart", parent)
        self._installButton.clicked.connect(self.install_update)
#         self._installButton.setEnabled(self._install_ready)
        layout.addWidget(self._installButton)
                
        widget.setMaximumHeight(widget.sizeHint().height())
        widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        
        return widget
    
    def has_git(self):
        try:
            return self.getGitCommandResult(["rev-parse"]) == 0
        except:
            return None
        
    def install_update(self):
        shutil.copy(UPDATE_SCRIPT, UPDATE_SCRIPT_EXEC_PATH)
        if os.path.isfile(UPDATE_SCRIPT_EXEC_PATH):
            args = [sys.executable, UPDATE_SCRIPT_EXEC_PATH, get_settings().get_resource(".")]
            log_info("Starting Update via git")
            if getPlatform() == PLATFORM_WINDOWS:
                subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
                get_server().call("HELO_STOP installer_update", client="127.0.0.1")
            else:
                subprocess.Popen(" ".join(args), shell=True, close_fds=True)
                get_server().call("HELO_STOP installer_update", client="127.0.0.1")
        else:
            log_error("Update Script was not found at %s"%UPDATE_SCRIPT_EXEC_PATH)
        
#     def git_version_info(self):
#         try:
#             _, self._version, __ = self.runGitCommand(["log", "-1"], self._lunchdir, quiet=False)
#             for line in self._version.splitlines():
#                 if line.startswith("Date:"):
#                     self._version_short = unicode(line[5:].strip())            
#         except:
#             log_exception("git log could not be executed correctly - version information not available")
#         
#         try:    
#             revListArgs = ["rev-list", "HEAD", "--count"]
#             ret, cco, _ = self.runGitCommand(revListArgs, self._lunchdir, quiet=False)
#             if ret:
#                 # something went wrong, get out of here!
#                 raise False
#             self._commit_count = cco.strip()
#             
#             if os.path.exists(self._external_plugin_dir):
#                 retCode, cco, __ = self.runGitCommand(revListArgs, self._external_plugin_dir, quiet=False)
#                 if retCode == 0:
#                     self._commit_count_plugins = cco.strip()
# 
    def runGitCommand(self, args, path = None, quiet = True):
        if path == None:
            path = get_settings().get_main_package_path()
         
        call = ["git","--no-pager","--git-dir="+path+"/.git","--work-tree="+path]
        call = call + args
         
        fh = subprocess.PIPE    
        if quiet:
            fh = open(os.path.devnull,"w")
        p = subprocess.Popen(call,stdout=fh, stderr=fh)
        pOut, pErr = p.communicate()
        retCode = p.returncode
        return retCode, pOut, pErr
     
    def getGitCommandResult(self, args, path = None, quiet = True):
        retCode, _, __ = self.runGitCommand(args, path, quiet)
        return retCode
         
    def canGitUpdate(self, repo=None):
        if self.getGitCommandResult(["rev-parse"], repo) != 0:
            return (False, "'%s' is no git repository" % repo)
         
        if self.getGitCommandResult(["diff","--name-only","--exit-code","--quiet"], repo) != 0:
            return (False, "There are unstaged changes")
         
        if self.getGitCommandResult(["diff","--cached","--exit-code","--quiet"], repo) != 0:
            return (False, "There are staged, uncommitted changes")
         
        _, branch, __ = self.runGitCommand(["symbolic-ref","HEAD"], repo, quiet=False)
        if "master" not in branch:
            return (False, "The selected branch is not the master branch")
         
        if self.getGitCommandResult(["log","origin/master..HEAD","--exit-code","--quiet"]) != 0:
            return (False, "There are unpushed commits on the master branch")
        
        return (True, None)
#     
#     def getCanUpdateMain(self):
#         return self.getCanUpdate(self._lunchdir)
#         
#     def getCanUpdatePlugins(self):
#         return self.getCanUpdate(self._main_config_dir + "/plugins/")