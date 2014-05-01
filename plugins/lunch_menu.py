from lunchinator.iface_plugins import iface_gui_plugin
import urllib2
from lunchinator.callables import AsyncCall
from lunchinator.utilities import getValidQtParent
    
class lunch_menu(iface_gui_plugin):
    def __init__(self):
        super(lunch_menu, self).__init__()
        self.options = {"url":"http://lunchinator.de/files/menu_dummy.txt" }
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from PyQt4.QtGui import QTextEdit, QSizePolicy
        self._textview = QTextEdit(parent)
        self._textview.setLineWrapMode(QTextEdit.WidgetWidth)
        self._textview.setReadOnly(True)
        self._textview.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        
        AsyncCall(getValidQtParent(), self._downloadText, self._updateText, self._errorDownloadingText)()
        
        return self._textview
    
    def _downloadText(self):
        resp = urllib2.urlopen(self.options["url"])
        return resp.read()
    
    def _updateText(self, txt):
        self._textview.setPlainText(txt)
        
    def _errorDownloadingText(self, msg):
        self._textview.setPlainText("Error downloading text: " + msg)
    
    def add_menu(self,menu):
        pass
