from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_plugin_manager
    
class list_plugins(iface_gui_plugin):
    def __init__(self):
        super(list_plugins, self).__init__()
        #self.options = {"url":"http://155.56.69.85:1081/lunch_de.txt" }
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
        
    def get_plugin_info(self):
        info = {}
        for pluginInfo in get_plugin_manager().getAllPlugins():   
            p = {}
            p["name"]=pluginInfo.name
#            txt+=pluginInfo.path +" "
#            txt+=pluginInfo.version +" "
            p["author"] = pluginInfo.author
#            txt+=pluginInfo.copyright +" "
#            txt+=pluginInfo.website +" "
            p["description"]=pluginInfo.description
            p["requirements"]=[]
            if pluginInfo.details.has_option("Requirements","pip"):
                p["requirements"] = pluginInfo.details.get("Requirements","pip").split(",")
            info[pluginInfo.name] = p
        return info
    
    def create_widget(self, parent):
        from listPluginsWidget import listPluginsWidget
        
        return listPluginsWidget(parent, self.get_plugin_info())
    
    
    def add_menu(self,menu):
        pass
    