from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_settings, get_server, get_db_connection

    
class stat_visualize(iface_gui_plugin):
    def __init__(self):
        super(stat_visualize, self).__init__()

        self.options = [((u"db_connection", u"DB Connection",
                          get_settings().get_available_db_connections()),
                         get_settings().get_default_db_connection())]
    
    def activate(self):
        iface_gui_plugin.activate(self)      
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)        
        
    def create_widget(self, parent):
        from stat_visualize.diagram import statTimelineTab, statSwarmTab
        from PyQt4.QtGui import QTabWidget,QLabel
        from PyQt4.QtCore import Qt
        
        connPlugin, plugin_type = get_db_connection(self.options["db_connection"])
        
        w = QTabWidget(parent)
        w.addTab(statTimelineTab(parent, connPlugin), "Timeline")
        w.addTab(statSwarmTab(parent, connPlugin), "Swarm")
        return w
    
    def add_menu(self, menu):
        pass

