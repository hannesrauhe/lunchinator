from lunchinator.plugin import iface_called_plugin
from lunchinator import get_server, get_settings
import urllib, urllib2, contextlib, base64, json, threading

class webrelay(iface_called_plugin):        
    def __init__(self):
        super(webrelay, self).__init__()
        self.options = [(("no_proxy", "Don't use proxy server", self._startCheckTimer),False),
                        ((u"server",u"Server", self._startCheckTimer),""),
                        ((u"polling_time",u"Number of Sec to pull new messages", self._startCheckTimer),10),
                        ((u"pushURL", u"URL to open when call comes in", self._startCheckTimer),
                         "/webrelay/addMessage.xsjs?group=$group$&message=$msg$&name=$name$&id=$id$"),
                        ((u"pullURL", u"URL to pull calls that should be send", self._startCheckTimer),
                         "/webrelay/getNewMessages.xsjs?group=$group$"),
                        ((u"http_user", u"User for HTTP Auth", self._startCheckTimer), ""),
                        ((u"http_pass", u"Password for HTTP Auth", self._startCheckTimer),"")]
        self.failed_attempts = 0
        self.timer = None
        self.timerRestartLock = threading.Lock()
        self.stop = False # set to True only on Deactivation of plugin
        
    def get_displayed_name(self):
        return u"WebRelay"
        
    def activate(self):
        iface_called_plugin.activate(self)
        self.stop = False
        self._startCheckTimer()
        
    def deactivate(self):
        with self.timerRestartLock:
            self.stop = True
            if self.timer:
                self.timer.cancel() 
                self.timer = None
        iface_called_plugin.deactivate(self)
        
    def process_message(self, msg, addr, member_info):
#         print member_info
        if self.options[u"server"]:
            self._pushCall({"msg":msg, "id":member_info[u"ID"] , "name":member_info[u"name"], "group":get_settings().get_group()})
        else:
            self.logger.error("WebRelay: please configure a server in Settings")
            
    def _fillUrlPlaceholders(self, url, info):
        retUrl = url
        
        for var in info.iterkeys():
            retUrl = retUrl.replace("$%s$"%var, urllib.quote_plus(info[var])) 
            
        #TODO (hannes) remove unknown placeholders
        return retUrl;
        
    def _pushCall(self, infos):
        push_url = self.options[u"server"] + self._fillUrlPlaceholders(self.options[u"pushURL"], infos)
        
        response = ""
        
        try:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(push_url, headers=hdr)
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
            self.logger.error("WebRelay HTTP Error %d: %s", err.code, err.reason)
           
        if response:
            resp = {}
            try: 
                resp = json.loads(response)
            except:
                self.logger.error("Invalid response from webserver after relaying call: %s", response)
                
            if not "success" in resp:
                self.logger.error("Webrelay: negative response from webserver after relaying call: %s", response)
                
    def _pullCalls(self):        
        pull_url = self.options[u"server"] + self._fillUrlPlaceholders(self.options[u"pullURL"], {"group":get_settings().get_group()})
         
        response = ""
        
        try:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(pull_url, headers=hdr)
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
            self.logger.error("WebRelay HTTP Error %d: %s", err.code, err.reason)
            self.failed_attempts+=1
            
        if response:
            resp = {}
            try: 
                resp = json.loads(response)
            except:
                self.logger.error("WebRelay: Invalid message when pulling calls from server: %s", response)
            self.failed_attempts = 0
            if len(resp):
                self.logger.debug("WebRelay: Pulled %d calls from server", len(resp))
                for c in resp:
                    if "sender" in c and "msg" in c:
                        get_server().call("Remote call from %s: %s"%(c["sender"],c["msg"]))
                    else:
                        self.logger.error("WebRelay: Malformed message: %s", c)
            
        self._startCheckTimer()
    
    def _startCheckTimer(self, _=None, __=None):
        self.logger.debug("WebRelay: Starting check Timer")
        
        if 0==len(self.options[u"server"]):
            self.logger.error("WebRelay: please configure a server in settings")
            return
            
        if self.failed_attempts < 5:
            timeout = self.options["polling_time"]
        else:
            timeout = 10*60 #too many failed attempts, I will try every ten minutes
            
        with self.timerRestartLock:            
            if not self.stop:
                try:
                    if self.timer:
                        self.timer.cancel()
                except:
                    self.logger.debug("WebRelay: failed to cancel the timer")
                self.timer = threading.Timer(timeout, self._pullCalls)
                self.timer.start()
            
