from lunchinator.plugin import iface_called_plugin
from lunchinator import get_server, get_settings, \
    get_notification_center, get_peers
from lunchinator.log import loggingFunc

from StringIO import StringIO
from threading import Thread
import SimpleHTTPServer, SocketServer, os, socket, contextlib, csv, time, sys

#http to serve the remote pictures component
class ExtendedHTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def log_message(self, _, *args):
        return
    
class http_server_thread(Thread):    
    def __init__(self, port,html_dir):
        super(http_server_thread, self).__init__()
        self.port = int(port)
        self.html_dir = html_dir
        self.server = None
        
    def run(self):
        os.chdir(self.html_dir)
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        self.server = SocketServer.TCPServer(("", self.port), ExtendedHTTPHandler)

        self.server.serve_forever()
        
    def stop_server(self):
        if self.server:            
            self.server.shutdown()
            
class raspicam(iface_called_plugin):
    def __init__(self):
        super(raspicam, self).__init__()
        self.options = [(("picture_path", "Folder where pics are stored"), os.path.join(get_settings().get_main_config_dir(),"raspicam")),
                        (("http_server", "start http server to enable remote pics"), True),
                        (("http_hostname", "hostname/IP of this lunchinator"), socket.getfqdn()),
                        (("http_port", "Port where pictures can be accessed"), 5000)]
        self.s_thread = None
        
    def activate(self):
        iface_called_plugin.activate(self)
        if not os.path.isdir(self.options["picture_path"]):
            os.mkdir(self.options["picture_path"])
            #if this throws activation will be canceled
        if self.options["http_server"]:
            self.logger.info("Starting the Raspicam HTTP Server on Port %d"%self.options["http_port"])
            self.s_thread = http_server_thread(self.options["http_port"],self.options["picture_path"])
            self.s_thread.start()
        
    def deactivate(self):
        if self.s_thread:
            self.logger.info("Stopping Raspicam HTTP Server")
            self.s_thread.stop_server()
            self.s_thread.join()
        iface_called_plugin.deactivate(self)  
    
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        if lunch_call:
            self.take_picture()
                
    def take_picture(self):
        import time
        import picamera
        
        filename = "raspicam.png"
        
        with picamera.PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            camera.capture(os.path.join(self.options["picture_path"], filename))
            self.logger.debug("Picture taken with camera")
        
        if self.options["http_server"]:
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter=' ', quotechar='"')
                pic_url = "http://%s:%d/%s" % (self.options["http_hostname"], self.options["http_port"], filename)
                writer.writerow([pic_url, "Picamera picture from " % time.strftime("%b %d %Y %H:%M"), "raspicam"])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue())
            
            
    def do_take_picture(self, cmd):
        try:
            self.take_picture()
        except:
            print "Error while taking picture:"
            print sys.exc_info()[0]
            

        