from lunchinator.iface_plugins import *
from time import localtime
import subprocess,sys,ctypes
from yapsy.PluginManager import PluginManagerSingleton
import threading, SimpleHTTPServer, SocketServer, os

class http_server_thread(threading.Thread):    
    def __init__(self, port,html_dir):
        self.port = int(port)
        self.html_dir = html_dir
        self.server = None
        threading.Thread.__init__(self)
        
    def run(self):
        os.chdir(self.html_dir)
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self.server = SocketServer.TCPServer(("", self.port), Handler)

        self.server.serve_forever()
        
        
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
        self.options = {"http_port":50002,"html_dir":self.ls.main_config_dir}
        
        
    def activate(self):
        iface_called_plugin.activate(self)
        self.logger.info("Starting the HTTP Server on Port %d"%self.options["http_port"])
        self.s_thread = http_server_thread(self.options["http_port"],self.options["html_dir"])
        self.s_thread.start()
        if not os.path.exists(self.options["html_dir"]+"/index.html"):
            self.write_info_html()
        
    def deactivate(self):
        self.logger.info("Stopping HTTP Server")
        if self.s_thread:
            self.s_thread.stop_server()
            self.s_thread.join()
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if cmd in ["HELO_INFO","HELO_DICT","HELO_REQUEST_DICT"]:
            self.write_info_html()
                
    def write_info_html(self):
        try:
            if len(self.ls.member_info)==0:
                indexhtml = open(self.options["html_dir"]+"/index.html","w")
                indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' >no peers\n")
                indexhtml.close()
                return
            
            table_data = {"ip":[""]*len(self.ls.member_info)}
            index = 0
            for ip,infodict in self.ls.member_info.iteritems():
                table_data["ip"][index] = ip
                for k,v in infodict.iteritems():
                    if not table_data.has_key(k):
                        table_data[k]=[""]*len(self.ls.member_info)
                    if k=="avatar" and os.path.exists(self.ls.avatar_dir+"/"+v):
                        table_data[k][index]="<img width='200' src=\"avatars/%s\" />"%v
                    else:
                        table_data[k][index]=v
                index+=1
                        
            indexhtml = open(self.options["html_dir"]+"/index.html","w")
            indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' ><table>\n")
            indexhtml.write("<tr>") 
            for th in table_data.iterkeys():
                indexhtml.write("<th>%s</th>"%th) 
            indexhtml.write("</tr>") 
            for i in range(0,len(self.ls.member_info)):
                indexhtml.write("<tr>") 
                for k in table_data.iterkeys():
                    indexhtml.write("<td>%s</td>"%table_data[k][i]) 
                indexhtml.write("</tr>") 
            indexhtml.write("</table>\n")
            indexhtml.write(self.ls.version)
            indexhtml.close()
        except:
            self.logger.error("HTTP plugin: problem while writing html file: %s"%sys.exc_info())