from lunchinator.plugin import iface_called_plugin
from lunchinator import get_server, get_settings, \
    get_notification_center, get_peers
from lunchinator.log import loggingFunc
import os

class raspicam(iface_called_plugin):
    def __init__(self):
        super(raspicam, self).__init__()
        self.options = [(("picture_path", "Folder where pics are stored"), get_settings().get_main_config_dir())]
    
    def activate(self):
        iface_called_plugin.activate(self)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)    
    
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        if lunch_call:
            self.take_picture()
                
    def take_picture(self):
        import time
        import picamera
        
        with picamera.PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            camera.capture(os.path.join(self.options["picture_path"], "raspicam.jpg"))
            self.logger.debug("Picture taken with camera")
            
    def do_take_picture(self, cmd):
        try:
            self.take_picture()
        except:
            print "Error while taking picture..."