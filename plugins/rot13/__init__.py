from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_server

class rot13(iface_gui_plugin):
    def __init__(self):
        super(rot13, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from rot13.rot13box import rot13box
        
        w = rot13box(parent)
        with get_server().get_messages():
            if len(get_server().get_messages()) > 0:
                w.encodeText(get_server().get_messages().getLatest()[2])
            
        return w
        
    def do_rot13(self, args):
        """
        Encryption, now for the command line.
        Usage: rot13 <text> [<text2> [...]]
        """
        import string
        from lunchinator.cli import LunchCLIModule
        rot13 = string.maketrans( 
            u"ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz", 
            u"NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")
        
        args = LunchCLIModule.getArguments(args)
        for aString in args:
            try:
                aString = aString.encode("utf-8")
                print string.translate(aString, rot13)
            except:
                self.logger.exception("Error encrypting string: %s", aString)
        
    def add_menu(self,menu):
        pass