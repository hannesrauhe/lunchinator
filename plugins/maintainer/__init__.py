from lunchinator.iface_plugins import *

from maintainer_gui import *

import time,subprocess

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.reports = []
        self.w = maintainer_gui(self)
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        return self.w.create_widget()
            
    def add_menu(self,menu):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if "HELO_INFO" in cmd:
            self.w.updateInfoTable()
        if cmd=="HELO_BUGREPORT_DESCR":
            self.reports.append((time.time(),ip,value))
            name = " [" + ip + "]"
            if member_info.has_key("name"):
                name = " [" + member_info["name"] + "]"
            subprocess.call(["notify-send", name, "new bug report"])
            