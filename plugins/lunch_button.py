from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_settings, get_server
import os
    
class lunch_button(iface_gui_plugin):
    def __init__(self):
        super(lunch_button, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def callForLunch(self):
        get_server().call("lunch")
    
    def create_widget(self, parent):
        from PySide.QtGui import QPushButton, QSizePolicy, QIcon
        from PySide.QtCore import QSize
        
        lunchIcon = QIcon(os.path.join(get_settings().get_lunchdir(), "images", "lunch.svg"))
        lunchButton = QPushButton(parent)
        lunchButton.setIcon(lunchIcon)
        lunchButton.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        lunchButton.setIconSize(QSize(64, 64))
        lunchButton.clicked.connect(self.callForLunch)
        return lunchButton
    
    def add_menu(self,menu):
        pass
