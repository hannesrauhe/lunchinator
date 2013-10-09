from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, log_exception

class rot13(iface_gui_plugin):
    def __init__(self):
        super(rot13, self).__init__()
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from rot13 import rot13box
        
        w = rot13box(parent)
        if get_server().messagesCount() > 0:
            w.encodeText(get_server().getMessage(0)[2])
            
        return w
        
    def do_rot13(self, args):
        """
        Encryption, now for the command line.
        Usage: rot13 <text> [<text2> [...]]
        """
        import string
        import shlex
        rot13 = string.maketrans( 
            u"ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz", 
            u"NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")
        
        args = shlex.split(args)
        for aString in args:
            print string.translate(aString, rot13)
        
    def add_menu(self,menu):
        pass