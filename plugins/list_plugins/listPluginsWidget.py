from ui_plugins import Ui_Plugins
from PyQt4.Qt import QWidget, QListWidgetItem
from PyQt4.QtCore import Qt
from lunchinator import log_error

class listPluginsWidget(QWidget):
    def __init__(self, parent, p_info):
        super(listPluginsWidget, self).__init__(parent)
        self.p_info = p_info
        self.ui = Ui_Plugins()
        self.ui.setupUi(self)
        self.create_plugin_view(False)
        self.ui.pluginView.setCurrentRow(0)
        
    def create_plugin_view(self, showAll = True):
        for p_name, p_info in self.p_info.iteritems():
            item = QListWidgetItem(p_name, self.ui.pluginView)
            item.setCheckState(Qt.Checked if p_info["activated"] else Qt.Unchecked)
            if p_info["forced"]:
                item.setForeground(Qt.gray)
                flags = item.flags()
                flags &= ~Qt.ItemIsUserCheckable
                item.setFlags(flags)
            item.setHidden(not showAll and p_info["forced"])
            self.ui.pluginView.addItem(item)
            
    def plugin_selected(self, current, old):
        if not current:
            return
        p = self.p_info[str(current.text())]
        self.ui.authorLabel.setText("Author: "+p["author"])
        self.ui.descriptionlabel.setText(p["description"])
        self.ui.requirementsView.clear()
        if len(p["requirements"])==0:
            self.ui.requirementsView.addItem("None")
            self.ui.requirementsView.setDisabled(True)
#             self.ui.requirementsView.setVisible(False)
        else:
#             self.ui.requirementsView.setVisible(True)
            for req in p["requirements"]:
                self.ui.requirementsView.addItem(req)
            self.ui.requirementsView.setDisabled(False)
            
    def install_req_clicked(self):
        plug = self.ui.pluginView.currentItem()
        reqs = self.p_info[str(plug.text())]["requirements"]
        from utilities import installPipDependencyWindows
        installPipDependencyWindows(reqs)
        
    def show_all_toggled(self, value):
        r = self.ui.pluginView.currentRow()
        self.ui.pluginView.clear()
        self.create_plugin_view(value)
        self.ui.pluginView.setCurrentRow(r)
        
    def activate_plugin_toggled(self, item):
        p_name = str(item.text())
        if item.checkState()==Qt.Checked and not self.p_info[p_name]["activated"]:
            log_error("Plugin Activation not yet implemented")
            
        if item.checkState()==Qt.Unchecked and self.p_info[p_name]["activated"]:
            log_error("Plugin Deactivation not yet implemented")