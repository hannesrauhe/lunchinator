from online_update.appupdate.app_update_handler import AppUpdateHandler
from lunchinator.utilities import getPlatform, PLATFORM_LINUX
import os
import subprocess

class ExternalUpdateHandler(AppUpdateHandler):
    """Used when Lunchinator updates are handled by the OS package management."""
    
    @classmethod
    def appliesToConfiguration(cls):
        if getPlatform() != PLATFORM_LINUX:
            return False
         
        try:
            call = ["dpkg", "-s", "lunchinator"]         
            fh = open(os.path.devnull,"w")
            p = subprocess.Popen(call,stdout=fh, stderr=fh)
            p.communicate()
            retCode = p.returncode
            if retCode == 0:
                return True
        except OSError:
            # dpkg probably does not exists
            pass
                
        try:
            call = "rpm -qa | grep lunchinator"         
            fh = open(os.path.devnull,"w")
            p = subprocess.Popen(call,stdout=fh, stderr=fh, shell=True)
            p.communicate()
            retCode = p.returncode
            if retCode == 0:
                return True
        except OSError:
            # dpkg probably does not exists
            pass
        
        return False  
    
    def _getInitialStatus(self):
        return u"Updates for the Lunchinator are managed by your OS."
        