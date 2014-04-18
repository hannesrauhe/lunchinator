from lunchinator.iface_plugins import iface_called_plugin
import SimpleHTTPServer, SocketServer, os, codecs
from lunchinator import get_server, get_settings, log_info, log_exception, log_debug,\
    get_peers
from threading import Thread

class ExtendedHTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
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
        

class lunch_http(iface_called_plugin):
    s_thread = None

    def __init__(self):
        super(lunch_http, self).__init__()
        self.options = {"http_port":50002,"html_dir":get_settings().get_main_config_dir()}
        
    def activate(self):
        iface_called_plugin.activate(self)
        log_info("Starting the HTTP Server on Port %d"%self.options["http_port"])
        self.s_thread = http_server_thread(self.options["http_port"],self.options["html_dir"])
        self.s_thread.start()
        if not os.path.exists(self.options["html_dir"]+"/index.html"):
            self.write_info_html()
        
    def deactivate(self):
        log_info("Stopping HTTP Server")
        if self.s_thread:
            self.s_thread.stop_server()
            self.s_thread.join()
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
    
    def process_event(self,cmd,_value,_ip,_member_info):
        if cmd in ["HELO_INFO","HELO_DICT","HELO_REQUEST_DICT"]:
            self.write_info_html()
                
    def write_info_html(self):
        try:
            # TODO write information about inactive peers?
            if len(get_peers().getActivePeers())==0:
                with codecs.open(self.options["html_dir"]+"/index.html","w",'utf-8') as indexhtml:
                    indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' >no peers\n")
                    return
            
            table_data = {"id":[""]*len(get_peers().getActivePeers())}
            index = 0
            for peerID in get_peers().getActivePeers():
                infodict = get_peers().getPeerInfo(peerID)
                if infodict == None:
                    infodict = {}
                table_data["id"][index] = peerID
                for k,v in infodict.iteritems():
                    if not table_data.has_key(k):
                        table_data[k]=[""]*len(get_peers().getActivePeers())
                    if k=="avatar" and os.path.isfile(get_settings().get_avatar_dir()+"/"+v):
                        table_data[k][index]="<img width='200' src=\"avatars/%s\" />"%v
                    else:
                        table_data[k][index]=v
                index+=1
                        
            with codecs.open(self.options["html_dir"]+"/index.html","w",'utf-8') as indexhtml:
                indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' ><table>\n")
                indexhtml.write("<tr>") 
                for th in table_data.iterkeys():
                    indexhtml.write("<th>%s</th>"%th) 
                indexhtml.write("</tr>") 
                for i in range(0,len(get_peers().getActivePeers())):
                    indexhtml.write("<tr>") 
                    for k in table_data.iterkeys():
                        indexhtml.write("<td>%s</td>"%table_data[k][i]) 
                    indexhtml.write("</tr>") 
                indexhtml.write("</table>\n")
                #indexhtml.write(get_settings().get_version())
        except:
            log_exception("HTTP plugin: problem while writing html file")