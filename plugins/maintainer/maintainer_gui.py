from lunchinator import get_server
from lunchinator.table_models import ExtendedMembersModel
from PyQt4.QtGui import QTreeView, QTabWidget, QSortFilterProxyModel, QSizePolicy
from PyQt4.QtCore import Qt
from maintainer.bug_reports_widget import BugReportsWidget
from maintainer.members_widget import MembersWidget
import os

class maintainer_gui(QTabWidget):
    LOG_REQUEST_TIMEOUT = 10 # 10 seconds until request is invalid
    def __init__(self,parent,mt):
        super(maintainer_gui, self).__init__(parent)
        self.info_table = None
        self.visible = False
        
        self.addTab(BugReportsWidget(parent, mt), "Bug Reports")        
        self.addTab(MembersWidget(parent), "Members")        
        self.addTab(self.create_info_table_widget(self), "Info")
        
        self.setCurrentIndex(0)
        self.visible = True
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        
    def update_dropdown_members(self):
        pass
    
    def create_info_table_widget(self, parent):
        self.info_table = QTreeView(parent)
        self.info_table.setSortingEnabled(True)
        self.info_table.setHeaderHidden(False)
        self.info_table.setAlternatingRowColors(True)
        self.info_table.setIndentation(0)
        
        self.info_table_model = ExtendedMembersModel(get_server())
        proxyModel = QSortFilterProxyModel(self.info_table)
        proxyModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxyModel.setDynamicSortFilter(True)
        proxyModel.setSourceModel(self.info_table_model)
        
        self.info_table.setModel(proxyModel)
        return self.info_table
        
    def destroy_widget(self):
        self.visible = False
    
class maintainer_wrapper(object):
    reports = []
    options = {u"github_token":"", u"repo_user":u"hannesrauhe", u"repo_name":u"lunchinator"}
    def __init__(self):
        tokenPath = os.path.join(os.path.expanduser("~"), ".github_token")
        if os.path.exists(tokenPath):
            with open(tokenPath) as tokenFile:
                token = tokenFile.readline()
                self.options[u"github_token"] = token
        
    def getBugsFromDB(self, _):
        return []
    
    def set_option(self, option, newValue, convert = True):
        print "set %s to '%s' (%s), convert: %s" % (option, newValue, type(newValue), convert)
    
if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : maintainer_gui(window, maintainer_wrapper()))
    