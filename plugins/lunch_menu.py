from lunchinator.iface_plugins import iface_gui_plugin
import urllib2
from PyQt4.QtGui import QTextEdit
    
class lunch_menu(iface_gui_plugin):
    def __init__(self):
        super(lunch_menu, self).__init__()
        self.options = {"url":"http://lunchinator.de/files/menu_dummy.txt" }
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        textview = QTextEdit(parent)
        textview.setLineWrapMode(QTextEdit.WidgetWidth)
        textview.setReadOnly(True)
        
        resp = urllib2.urlopen(self.options["url"])
        txt = resp.read()
        textview.setPlainText(txt)
        return textview
    
    def add_menu(self,menu):
        pass
