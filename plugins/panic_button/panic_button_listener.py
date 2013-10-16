import usb, time
from lunchinator import log_error, log_info, get_server
from threading import Thread

class panic_button_listener(Thread):
    idVendor = None
    idProduct = None
    running = True
    msg = "lunch panic"
    
    def __init__(self,idV,idP,msg):
        super(panic_button_listener, self).__init__()
        self.idVendor = idV
        self.idProduct = idP
        self.msg = msg      

    def findButton(self):
        for bus in usb.busses():
            for dev in bus.devices:
                #TODO (Hannes): read from options
                if dev.idVendor == 0x1d34 and dev.idProduct == 0x000d:
                    return dev
        return None
                
    def run(self):    
        dev = self.findButton()
        if dev == None:
            log_error("Cannot find panic button device")
            return
        handle = dev.open()
        interface = dev.configurations[0].interfaces[0][0]
        endpoint = interface.endpoints[0]
        
        try:
            handle.detachKernelDriver(interface)
        except Exception, _:
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
                        log_info("pressed the Panic Button")
                        get_server().call_all_members(self.msg)
                    unbuffer = True
                else:
                    unbuffer = False
                #print [hex(x) for x in result]
            except Exception, _:
                # Sometimes this fails. Unsure why.
                pass
        
            time.sleep(endpoint.interval / float(1000))
        
        handle.releaseInterface()
        
    def stop_daemon(self):
        self.running = False