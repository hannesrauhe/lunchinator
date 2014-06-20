from lunchinator.iface_plugins import iface_gui_plugin
import urllib2, contextlib
from lunchinator.callables import AsyncCall
from lunchinator.utilities import getValidQtParent
    
class lunch_menu(iface_gui_plugin):
    def __init__(self):
        super(lunch_menu, self).__init__()
        self.options = [(("no_proxy", "Don't use proxy server"),False),
                        (("url", "URL"),"http://lunchinator.de/files/menu_dummy.txt")]

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
        if self.options["no_proxy"]:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(self.options["url"], headers=hdr)
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)   
            with contextlib.closing(opener.open(req)) as u:
                return u.read
            
        resp = urllib2.urlopen(self.options["url"])
        return resp.read()
    
    def _updateText(self, txt):
        self._textview.setPlainText(txt)
        
    def _errorDownloadingText(self, msg):
        self._textview.setPlainText("Error downloading text: " + msg)
    
    def add_menu(self,menu):
        pass
