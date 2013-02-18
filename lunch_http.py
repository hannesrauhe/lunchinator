import lunch_default_config
import threading, SimpleHTTPServer, SocketServer, os

class lunch_http(threading.Thread):
    config = None
    server = None
    
    def __init__(self, config):
        self.config = config
        threading.Thread.__init__(self)
        
    def run(self):
        print "Starting the HTTP Server on Port",self.config.http_port
        os.chdir(self.config.html_dir)
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self.server = SocketServer.TCPServer(("", self.config.http_port), Handler)

        self.server.serve_forever()
        
        print "Stopping HTTP Server"
        
    def stop_server(self):            
        self.server.shutdown()