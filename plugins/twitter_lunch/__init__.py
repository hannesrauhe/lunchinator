from lunchinator.iface_plugins import iface_called_plugin
import subprocess, sys, ctypes
from lunchinator import get_server, log_exception, log_warning, get_settings, convert_string, log_error, log_info, log_debug
import urllib2, tempfile, json, time, twitter, contextlib

from threading import Thread,Event,Lock

class TwitterDownloadThread(Thread):    
    def __init__(self, event):
        super(TwitterDownloadThread, self).__init__()
        self._twitter_api = None
        self._own_screen_name = ""
        self._screen_names = []
        self._old_pic_urls = {}
        self._since_ids = {}
        self._stop_event = event
        self._lock = Lock()
        self._polling_time = 60
        self._mentions_since_id = 0
        self._remote_callers = []
        
    def set_polling_time(self,v):
        self._polling_time = v
                    
    def get_screen_names(self):
        return self._screen_names
                    
    def add_screen_name(self,s):
        with self._lock:
            if not s.toUpper() in [x.toUpper() for x in self._screen_names]:
                self._screen_names.append(s)
                if not self._old_pic_urls.has_key(s):
                    self._old_pic_urls[s]=""
                if not self._since_ids.has_key(s):
                    self._since_ids[s]=0
                    
    def get_remote_callers(self):
        return self._remote_callers
                    
    def add_remote_caller(self,value):
        remote_caller = value[1:] if value[0]=="@" else value
        with self._lock:
            if not remote_caller in self._remote_callers:
                self._remote_callers.append(remote_caller)
            
    def authenticate(self,key,secret,at_key,at_secret):
        with self._lock:
            if len(key) and len(secret) and len(at_key) and len(at_secret):
                try:
                    self._twitter_api = twitter.Api(consumer_key=key,
                                 consumer_secret=secret,
                                 access_token_key=at_key,
                                 access_token_secret=at_secret,
                                 debugHTTP=False)
                    self._mentions_since_id = 0
                except:
                    log_exception("Twitter: authentication with twitter failed: check settings")
                    self._twitter_api = None
                    return False
                try:
                    self._own_screen_name = self._twitter_api.VerifyCredentials().GetScreenName()
                except:
                    log_exception("Twitter: was not able to find my screen_name")
                    self._twitter_api = None
                    return False
                    
            else:
                log_error("Twitter: provide keys and secrets in settings")
                self._twitter_api = None
                return False

    def _get_pics_from_account(self,account_name):
        with self._lock:
            urls = []
            tweets = self._twitter_api.GetUserTimeline(screen_name=account_name,since_id=self._since_ids[account_name])
            if 0==len(tweets):
                log_debug(("Twitter: no new tweets from %s since"%str(account_name)),self._since_ids[account_name])
                return
            
            self._since_ids[account_name] = tweets[0].GetId()
            
            try:
                for media in tweets[0].media:
                    urls.append((media["media_url"],tweets[0].text))
            except:
                item = tweets[0].AsDict()
                urls = [(url,item['text']) for url in item['text'].split(" ") if url.startswith("http")]  
                 
            log_debug("Twitter: from %s extracted URLs: %s"%(str(account_name),str(urls)))  
            if len(urls):
            #for u in urls:
                u = urls[0]
                get_server().call("HELO_REMOTE_PIC %s %s:%s"%(u[0],account_name,u[1]))
                
    def _find_remote_calls(self):
        get_server().call("HELO_TWITTER_REMOTE %s"%self._own_screen_name)          
        with self._lock:        
            if 0 == self._mentions_since_id:
                #determine the start
                ments = self._twitter_api.GetMentions(count=1)
                if len(ments):
                    self._mentions_since_id = ments[0].GetId()
                else:
                    self._mentions_since_id = 1
                log_debug("Twitter: Starting with mentions ID",self._mentions_since_id)            
            
            ments = self._twitter_api.GetMentions(since_id=self._mentions_since_id)
            if 0==len(ments):
                log_debug("Twitter: Nobody mentioned me since",self._mentions_since_id)
                return
            self._mentions_since_id = ments[0].GetId()
            for m in ments:
                log_debug("Twitter: I was mentioned:",m.GetUser(),m.GetText())
                s_name = m.GetUser().GetScreenName()
                if s_name not in self._remote_callers:
                    log_debug("Twitter: I do not know him")
                    continue
                get_server().call("Remote call by @%s: %s"%(s_name,m.GetText()))            
        
                
    def run(self):        
        while not self._stop_event.wait(self._polling_time):
            if None==self._twitter_api:
                continue
            log_debug("Polling Twitter now")
            for account_name in self._screen_names:
                try:
                    self._get_pics_from_account(account_name)
                except:
                    log_exception("Twitter: Error while accessing twitter timeline of user ",account_name)
            
            self._find_remote_calls()

class twitter_lunch(iface_called_plugin):
    def __init__(self):
        super(twitter_lunch, self).__init__()
        self.options = [(("twitter_pics","Extract pictures from following Twitter accounts:",self.set_twitter_pics),"HistoricalPics"),
                        (("key","API Key"),""),
                        (("secret","API Secret"),""),
                        (("at_key","Access Token Key"),""),
                        (("at_secret","Access Token Secret", self.authenticate),""),
                        (("polling_time","Polling Time", self.reset_timer),60)]
        self.dthread = None
        self.stopEvent = Event()
        
    def activate(self):        
        iface_called_plugin.activate(self)
        
        self.dthread = TwitterDownloadThread(self.stopEvent)
        self.authenticate()
        self.set_twitter_pics()
        self.reset_timer()
        
        self.dthread.start()
    
    def deactivate(self):
        log_info("Stopping Twitter Thread")
        self.set_option("twitter_pics",";;".join(self.dthread.get_screen_names()))
        self.stopEvent.set()
        #TODO: join thread
        iface_called_plugin.deactivate(self)
        
    def authenticate(self,oldv=None,newv=None):
        self.dthread.authenticate(self.options["key"],self.options["secret"],self.options["at_key"],self.options["at_secret"])
    
    def reset_timer(self,oldv=None,newv=None):
        self.dthread.set_polling_time(self.options["polling_time"])
        
    def set_twitter_pics(self,oldv=None,newv=None):
        for sname in self.options["twitter_pics"].split(";;"):
            self.dthread.add_screen_names(s_name)
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        if cmd=="HELO_REQUEST_TWITTER_PIC":
            self.dthread.add_screen_name(value)
            log_debug("Now following these streams for pics:",str(self.dthread.get_screen_names()))
        elif cmd=="HELO_TWITTER_USER":
            self.dthread.add_remote_caller(value)
            log_debug("Now accepting remote calls from:",str(self.dthread.get_remote_callers()))            

    def process_message(self,msg,addr,member_info):
        pass        
