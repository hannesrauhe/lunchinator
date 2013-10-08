from lunchinator.iface_plugins import *

class bug_report(iface_gui_plugin):
    def __init__(self):
        super(bug_report, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from bug_report.bug_report_gui import bug_report_gui
        return bug_report_gui(parent)
            
    def add_menu(self,menu):
        pass
