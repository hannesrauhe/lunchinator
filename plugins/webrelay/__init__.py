from lunchinator.plugin import iface_called_plugin
from lunchinator import log_error
import urllib, urllib2, contextlib, base64, json

class webrelay(iface_called_plugin):        
    def __init__(self):
        super(webrelay, self).__init__()
        self.options = [(("no_proxy", "Don't use proxy server"),False),
                        ((u"server",u"Server"),""),
                        ((u"callURL", u"URL to open when call comes in"),
                         "/webrelay/addMessage.xsjs?message=$msg$&name=$name$&id=$id$"),
                        ((u"http_user", u"User for HTTP Auth"), ""),
                        ((u"http_pass", u"Password for HTTP Auth"),"")]
        
    def process_message(self, msg, addr, member_info):
#         print member_info
        if self.options[u"server"]:
            self._registerCall({"msg":msg, "id":member_info[u"ID"] , "name":member_info[u"name"]})
        else:
            log_error("WebRelay: please configure a server in Settings")
        
    def _registerCall(self, infos):
        call_url = self.options[u"callURL"]       
        
        for var in ["msg","name","id"]:
            call_url = call_url.replace("$%s$"%var, urllib.quote_plus(infos[var])) 

        call_url = self.options[u"server"] + call_url
        
        response = ""
        
        try:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(call_url, headers=hdr)
            if self.options[u"http_user"]:
                base64string = base64.encodestring('%s:%s' % (self.options[u"http_user"], self.options[u"http_pass"])).replace('\n', '')
                req.add_header("Authorization", "Basic %s" % base64string)  
            
            if self.options["no_proxy"]:
                proxy_handler = urllib2.ProxyHandler({})
                opener = urllib2.build_opener(proxy_handler)   
                with contextlib.closing(opener.open(req)) as u:
                    response=u.read()
            else:
                with contextlib.closing(urllib2.urlopen(req)) as u:
                    response = u.read()
        except urllib2.HTTPError, err:
            log_error("WebRelay HTTP Error %d: %s"%(err.code, err.reason))
           
        if response:
            resp = {}
            try: 
                resp = json.loads(response)
            except:
                log_error("Invalid response from webserver after relaying call: "+response)
                
            if not "success" in resp:
                log_error("Webrelay: negative response from webserver after relaying call: "+response)
            
            