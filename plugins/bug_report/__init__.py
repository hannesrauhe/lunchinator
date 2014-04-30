from lunchinator.iface_plugins import *

class bug_report(iface_gui_plugin):
    def __init__(self):
        super(bug_report, self).__init__()
        self.options = [((u"repo_name", "GitHub Repository Name", self.repoChanged), ""),
                        ((u"repo_user", "GitHub Repository Owner", self.repoChanged), "")]
        self.repoUpdated = False
        self.gui = None
                
    def repoChanged(self, _key, _newVal):
        self.repoUpdated = True
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from bug_report.bug_reports_widget import BugReportsWidget
        self.gui = BugReportsWidget(parent, self) 
        return self.gui
            
    def add_menu(self,menu):
        pass

    def save_options_widget_data(self):
        iface_gui_plugin.save_options_widget_data(self)
        if self.repoUpdated:
            self.repoUpdated = False
            if self.gui != None:
                self.gui.repoChanged()
            