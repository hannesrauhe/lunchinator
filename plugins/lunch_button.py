from lunchinator.iface_plugins import iface_gui_plugin
    
class lunch_button(iface_gui_plugin):
    def __init__(self):
        super(lunch_button, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from lunchinator.lunch_button import LunchButton
        return LunchButton(parent)
    
    def add_menu(self,menu):
        pass
