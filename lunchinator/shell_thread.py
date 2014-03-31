from PyQt4.QtCore import QThread, pyqtSignal
import subprocess, os
from lunchinator import log_exception
   
class ShellThread(QThread):
    finished = pyqtSignal(QThread, int)
    error = pyqtSignal(QThread)
    
    def __init__(self, parent, args, quiet = True, context = None):
        super(ShellThread, self).__init__(parent)

        self.args = args
        self.quiet = quiet
        self.context = context
        self.pOut = None
        self.pErr = None
        self.exitCode = 0
    
    def run(self):
        try:
            fh = subprocess.PIPE    
            if self.quiet:
                fh = open(os.path.devnull,"w")
            p = subprocess.Popen(self.args,stdout=fh, stderr=fh)
            self.pOut, self.pErr = p.communicate()
            self.exitCode = p.returncode
            self.finished.emit(self, self.exitCode)
        except:
            log_exception("Error executing shell command", self.args)
            self.error.emit(self)
        