from ui_plugins import Ui_Plugins
from PyQt4.Qt import QWidget, QListWidgetItem
from PyQt4.QtCore import Qt
from lunchinator import log_error, get_plugin_manager, get_notification_center

class listPluginsWidget(QWidget):
    def __init__(self, parent):
        super(listPluginsWidget, self).__init__(parent)
        self.ui = Ui_Plugins()
        self.ui.setupUi(self)
        
        self.p_info = self.get_plugin_info()
        
        self.create_plugin_view(False)
        self.ui.pluginView.setCurrentRow(0) 
        
        get_notification_center().connectPluginActivated(self.update_plugin_view)  
        get_notification_center().connectPluginDeactivated(self.update_plugin_view)  
        
    def finish(self):
        get_notification_center().disconnectPluginActivated(self.update_plugin_view)  
        get_notification_center().disconnectPluginDeactivated(self.update_plugin_view) 
    
    def get_plugin_info(self):
        info = {}
        for pluginInfo in get_plugin_manager().getAllPlugins(): 
            short_name = pluginInfo.plugin_object.get_displayed_name()  
            p = {}
            p["name"] = pluginInfo.name if not short_name else short_name
            p["full_name"] = pluginInfo.name
            p["categories"] = pluginInfo.categories
            p["author"] = pluginInfo.author
#            txt+=pluginInfo.path +" "
#            txt+=pluginInfo.version +" "
#            txt+=pluginInfo.copyright +" "
#            txt+=pluginInfo.website +" "
            p["description"] = pluginInfo.description
            p["requirements"] = []
            if pluginInfo.details.has_option("Requirements", "pip"):
                p["requirements"] = pluginInfo.details.get("Requirements", "pip").split(",")
            p["forced"] = pluginInfo.plugin_object.force_activation
            p["activated"] = pluginInfo.plugin_object.is_activated
            info[pluginInfo.name] = p
        return info
        
    def create_plugin_view(self, showAll = True):
        for p_name, p_info in self.p_info.iteritems():
            item = QListWidgetItem(p_info["name"], self.ui.pluginView)
            item.setToolTip(p_name)
            item.setCheckState(Qt.Checked if p_info["activated"] else Qt.Unchecked)
            if p_info["forced"]:
                item.setForeground(Qt.gray)
                flags = item.flags()
                flags &= ~Qt.ItemIsUserCheckable
                item.setFlags(flags)
            
            #deactivate toggling of gui plugins for now
            if "gui" in p_info["categories"]:
                flags = item.flags()
                flags &= ~Qt.ItemIsUserCheckable
                item.setFlags(flags)

            item.setHidden(not showAll and p_info["forced"])
            self.ui.pluginView.addItem(item)
            
    def update_plugin_view(self):
        self.p_info = self.get_plugin_info()
        r = self.ui.pluginView.currentRow()
        self.ui.pluginView.clear()
        self.create_plugin_view(self.ui.showAllCheckBox.checkState()==Qt.Checked)
        self.ui.pluginView.setCurrentRow(r)        
            
    def plugin_selected(self, current, old):
        if not current:
            return
        p = self.p_info[str(current.toolTip())]
        self.ui.authorLabel.setText("Author: "+p["author"])
        self.ui.descriptionlabel.setText(p["description"])
        self.ui.requirementsView.clear()
        if len(p["requirements"])==0:
            self.ui.requirementsView.addItem("None")
            self.ui.requirementsView.setDisabled(True)
            self.ui.installReqButton.setDisabled(True)
#             self.ui.requirementsView.setVisible(False)
        else:
#             self.ui.requirementsView.setVisible(True)
            for req in p["requirements"]:
                self.ui.requirementsView.addItem(req)
            self.ui.requirementsView.setDisabled(False)
            self.ui.installReqButton.setDisabled(False)
            
    def install_req_clicked(self):
        plug = self.ui.pluginView.currentItem()
        reqs = self.p_info[str(plug.toolTip())]["requirements"]
        from utilities import installPipDependencyWindows
        installPipDependencyWindows(reqs)
        
    def show_all_toggled(self, value):
        r = self.ui.pluginView.currentRow()
        self.ui.pluginView.clear()
        self.create_plugin_view(value)
        self.ui.pluginView.setCurrentRow(r)
        
    def activate_plugin_toggled(self, item):
        p_name = str(item.toolTip())
        if item.checkState()==Qt.Checked and not self.p_info[p_name]["activated"]:
            get_plugin_manager().activatePluginByName(\
                          self.p_info[p_name]["full_name"], self.p_info[p_name]["categories"][0])
            
            self.p_info[p_name]["activated"]=True
            
        if item.checkState()==Qt.Unchecked and self.p_info[p_name]["activated"]:
            get_plugin_manager().deactivatePluginByName(\
                          self.p_info[p_name]["full_name"], self.p_info[p_name]["categories"][0])
            
            self.p_info[p_name]["activated"]=False