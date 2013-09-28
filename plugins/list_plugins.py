from lunchinator.iface_plugins import iface_gui_plugin, PluginManagerSingleton
from PyQt4.QtGui import QTextEdit
    
class list_plugins(iface_gui_plugin):
    def __init__(self):
        super(list_plugins, self).__init__()
        #self.options = {"url":"http://155.56.69.85:1081/lunch_de.txt" }
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        textView = QTextEdit(parent)
        textView.setLineWrapMode(QTextEdit.WidgetWidth)
        textView.setReadOnly(True)
        
        txt = ""
        manager = PluginManagerSingleton.get()
        for pluginInfo in manager.getAllPlugins():    
            txt+=pluginInfo.name + " - "
#            txt+=pluginInfo.path +" "
#            txt+=pluginInfo.version +" "
#            txt+=str(pluginInfo.author) +", "
#            txt+=pluginInfo.copyright +" "
#            txt+=pluginInfo.website +" "
            txt+=pluginInfo.description +" "
#            txt+=pluginInfo.details + " "
            txt+="\n\n"
        textView.setPlainText(txt)
        return textView
    
    def add_menu(self,menu):
        pass
