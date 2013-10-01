from lunchinator.iface_plugins import iface_general_plugin
import usb
from lunchinator import get_server, log_info, log_error
    
class panic_button(iface_general_plugin):
    panic_thread = None
    
    def __init__(self):
        super(panic_button, self).__init__()
        self.options={"idVendor":"0x1d34",
                      "idProduct":"0x000d",
                      "panic_msg":"lunch panic" }
        
    def activate(self):
        from panic_button.panic_button_listener import panic_button_listener
        iface_general_plugin.activate(self)
        log_info("Starting panic button listener")
        self.panic_thread = panic_button_listener(self.options["idVendor"],self.options["idProduct"],self.options["panic_msg"])
        self.panic_thread.start()
        
        
    def deactivate(self):
        log_info("Stopping panic button listener")
        if self.panic_thread:
            self.panic_thread.stop_daemon()
            #TODO: self.panic_thread.join()
        iface_general_plugin.deactivate(self)

