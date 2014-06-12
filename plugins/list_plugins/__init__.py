from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_plugin_manager
    
class list_plugins(iface_gui_plugin):
    def __init__(self):
        super(list_plugins, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def get_plugin_info(self):
        info = {}
        for pluginInfo in get_plugin_manager().getAllPlugins(): 
            short_name = pluginInfo.plugin_object.get_displayed_name()  
            p = {}
            p["name"] = pluginInfo.name if not short_name else short_name
            p["full_name"] = pluginInfo.name
#            txt+=pluginInfo.path +" "
#            txt+=pluginInfo.version +" "
            p["author"] = pluginInfo.author
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
    
    def create_widget(self, parent):
        from listPluginsWidget import listPluginsWidget
        
        return listPluginsWidget(parent, self.get_plugin_info())
    
    
    def add_menu(self, menu):
        pass
    
