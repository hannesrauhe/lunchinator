
from iface_plugins import *
from time import localtime
import subprocess,sys,ctypes
from yapsy.PluginManager import PluginManagerSingleton
import lunch_default_config
import threading, SimpleHTTPServer, SocketServer, os

class http_server_thread(threading.Thread):
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
        if self.server:            
            self.server.shutdown()
        

class lunch_http(iface_called_plugin):
    s_thread = None
    ls = None
    
    def __init__(self):
        super(lunch_http, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_called_plugin.activate(self)
        self.s_thread = http_server_thread(self.ls)
        self.s_thread.start()
        if not os.path.exists(self.ls.html_dir+"/index.html"):
            self.write_info_html()
        
    def deactivate(self):
        print "trying to stop HTTP Server"
        if self.s_thread:
            self.s_thread.stop_server()
            self.s_thread.join()
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if cmd in ["HELO_INFO","HELO_DICT","HELO_MASTER"]:
            self.write_info_html()
                
    def write_info_html(self):
        try:
            indexhtml = open(self.ls.html_dir+"/index.html","w")
            indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' ><table>\n")
            if len(self.ls.member_info)>0:
                for ip,d in self.ls.member_info.iteritems():
                    indexhtml.write("<tr><td>"+str(ip)+"</td>\n")
                    if d.has_key("avatar") and d["avatar"] and os.path.exists(self.ls.avatar_dir+"/"+d["avatar"]):
                        indexhtml.write("<td><img width='200' src=\"avatars/"+d["avatar"]+"\" /></td>\n")
                    else:
                        indexhtml.write("<td></td>\n")
                    indexhtml.write("<td>")
                    for k,v in d.iteritems():
                        indexhtml.write(k+": "+v+"<br />\n")                
                    indexhtml.write("</td></tr>\n")
            indexhtml.write("</table>\n")
            indexhtml.write(self.ls.version)
            indexhtml.close()
        except:
            print "problem while writing html file"