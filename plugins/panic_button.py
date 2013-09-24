from lunchinator.iface_plugins import *
import gtk,gobject,urllib2,sys,threading
import time,usb,subprocess
from lunchinator import get_server, log_info
    
class panic_button(iface_general_plugin):
    panic_thread = None
    
    def __init__(self):
        super(panic_button, self).__init__()
        self.options={"idVendor":"0x1d34",
                      "idProduct":"0x000d",
                      "panic_msg":"lunch panic" }
        
    def activate(self):
        iface_general_plugin.activate(self)
        log_info("Starting panic button listener")
        self.panic_thread = panic_button_listener(self.options["idVendor"],self.options["idProduct"],self.options["panic_msg"])
        self.panic_thread.start()
        
        
    def deactivate(self):
        log_info("Stopping panic button listener")
        if self.panic_thread:
            self.panic_thread.stop_daemon()
            self.panic_thread.join()
        iface_general_plugin.deactivate(self)
    
class panic_button_listener(threading.Thread):
    idVendor = None
    idProduct = None
    running = True
    msg = "lunch panic"
    
    def __init__(self,idV,idP,msg):
        self.idVendor = idV
        self.idProduct = idP
        self.msg = msg      
        threading.Thread.__init__(self)  

    def findButton(self):
        for bus in usb.busses():
            for dev in bus.devices:
                #TODO (Hannes): read from options
                if dev.idVendor == 0x1d34 and dev.idProduct == 0x000d:
                    return dev
                
    def run(self):    
        dev = self.findButton()
        handle = dev.open()
        interface = dev.configurations[0].interfaces[0][0]
        endpoint = interface.endpoints[0]
        
        try:
            handle.detachKernelDriver(interface)
        except Exception, e:
            # It may already be unloaded.
            pass
        
        handle.claimInterface(interface)
        
        unbuffer = False
        while self.running:
            # USB setup packet. I think it's a USB HID SET_REPORT.
            result = handle.controlMsg(requestType=0x21, # OUT | CLASS | INTERFACE
            request= 0x09, # SET_REPORT
            value= 0x0200, # report type: OUTPUT
            buffer="\x00\x00\x00\x00\x00\x00\x00\x02")
        
            try:
                result = handle.interruptRead(endpoint.address, endpoint.maxPacketSize)
                if 22==result[0]:
                    if not unbuffer:
                        print "pressed the Panic Button"
                        get_server().call_all_members(self.msg)
                    unbuffer = True
                else:
                    unbuffer = False
                #print [hex(x) for x in result]
            except Exception, e:
                # Sometimes this fails. Unsure why.
                pass
        
            time.sleep(endpoint.interval * 0.001) # 10ms
        
        handle.releaseInterface()
        
    def stop_daemon(self):
        self.running = False
