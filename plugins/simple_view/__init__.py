from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, log_exception

class simple_view(iface_gui_plugin):
    def __init__(self):
        super(simple_view, self).__init__()
        self.w = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        if self.w != None:
            self.w.finish()           
        iface_gui_plugin.deactivate(self)
        
    def create_widget(self, parent):
        from simple_view.simpleViewWidget import SimpleViewWidget
        
        self.w = SimpleViewWidget(parent)
            
        return self.w
        
    def create_menus(self, menuBar):
        if self.w:
            menu = self.w.create_menu(menuBar)
            return [menu]
            