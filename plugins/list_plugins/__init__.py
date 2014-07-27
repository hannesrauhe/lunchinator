from lunchinator.plugin import iface_gui_plugin
    
class list_plugins(iface_gui_plugin):
    def __init__(self):
        super(list_plugins, self).__init__()
        self.w = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        if self.w != None:
            self.w.finish()
            self.w = None
    
    def create_widget(self, parent):
        from listPluginsWidget import listPluginsWidget
        
        self.w = listPluginsWidget(parent)
        return self.w
    
    
    def add_menu(self, menu):
        pass
    
