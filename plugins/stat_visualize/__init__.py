from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, log_error, get_settings, get_server, get_db_connection

    
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
        from stat_visualize.diagram import statTimelineWidget
        from PyQt4.QtGui import QGridLayout, QLabel, QPushButton, QWidget, QSpinBox
        from PyQt4.QtCore import Qt
        
        connPlugin, plugin_type = get_db_connection(self.options["db_connection"])
        
        w = QWidget(parent)
        lay = QGridLayout(w)
        vw = statTimelineWidget(connPlugin)
        lay.addWidget(vw,0,0,1,2)
        lay.addWidget(QLabel("Scale:"),1,0, Qt.AlignRight)
        spinbox = QSpinBox(parent)
        spinbox.setValue(vw.getScale())
        spinbox.valueChanged.connect(vw.setScale)
        lay.addWidget(spinbox,1,1)
        return w
    
    def add_menu(self,menu):
        pass

