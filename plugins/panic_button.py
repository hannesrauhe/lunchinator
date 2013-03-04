
from iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
import gtk,gobject,urllib2,sys,threading
import time
import usb
import lunch_client
import subprocess
    
class panic_button(iface_called_plugin):
    ls = None
    panic_thread = None
    
    def __init__(self):
        super(panic_button, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_gui_plugin.activate(self)
        if not self.hasConfigOption("idVendor"):
            self.setConfigOption("idVendor","0x1d34")
        if not self.hasConfigOption("idProduct"):
            self.setConfigOption("idProduct","0x000d" )
        self.panic_thread = panic_button_listener(self.getConfigOption("idVendor"),self.getConfigOption("idProduct"))
        self.panic_thread.start()
        
        
    def deactivate(self):
        print "Stopping panic button listener"
        if self.panic_thread:
            self.panic_thread.stop_daemon()
            self.panic_thread.join()
        iface_gui_plugin.deactivate(self)
    
    

class panic_button_listener(threading.Thread):
    idVendor = None
    idProduct = None
    running = True
    
    def __init__(self,idV,idP):
        self.idVendor = idV
        self.idProduct = idP        

    def findButton(self):
        for bus in usb.busses():
            for dev in bus.devices:
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
                        print "pressed"
                    unbuffer = True
                else:
                    unbuffer = False
                #print [hex(x) for x in result]
            except Exception, e:
                # Sometimes this fails. Unsure why.
                pass
        
            time.sleep(endpoint.interval * 0.001) # 10ms
        
        handle.releaseInterface(interface)
        
    def stop_daemon(self):
        self.running = False
