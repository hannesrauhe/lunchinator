from yapsy.PluginManager import PluginManagerSingleton
from lunchinator.iface_plugins import *

from bug_report_gui import *

class bug_report(iface_gui_plugin):
    ls = None
    
    def __init__(self):
        super(bug_report, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        self.w = bug_report_gui(self.ls)
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        return self.w.create_widget()
            
    def add_menu(self,menu):
        pass