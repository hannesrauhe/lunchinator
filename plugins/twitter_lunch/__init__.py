from lunchinator.iface_plugins import iface_called_plugin
import subprocess, sys, ctypes
from lunchinator import get_server, log_exception, log_warning, get_settings, convert_string, log_error, log_info, log_debug
import urllib2, tempfile, json, time, twitter, contextlib

from threading import Thread,Event,Lock

class TwitterDownloadThread(Thread):    
    def __init__(self, event):
        super(TwitterDownloadThread, self).__init__()
        self._twitter_api = None
        self._screen_names = []
        self._old_pic_urls = {}
        self._stop_event = event
        self._lock = Lock()
        self._polling_time = 60
        
    def set_polling_time(self,v):
        self._polling_time = v
            
    def set_screen_names(self,vlist):
        with self._lock:
            self._screen_names = vlist
            for s in vlist:
                if not self._old_pic_urls.has_key(s):
                    self._old_pic_urls[s]=""
            
    def authenticate(self,key,secret,at_key,at_secret):
        with self._lock:
            if len(key) and len(secret) and len(at_key) and len(at_secret):
                try:
                    self._twitter_api = twitter.Api(consumer_key=key,
                                 consumer_secret=secret,
                                 access_token_key=at_key,
                                 access_token_secret=at_secret,
                                 debugHTTP=False)
                    return True
                except:
                    log_exception("Twitter: authentication with twitter failed: check settings")
                    self._twitter_api = None
                    return False
            else:
                log_error("Twitter: provide keys and secrets in settings")
                self._twitter_api = None
                return False
        
    def run(self):        
        while not self._stop_event.wait(self._polling_time):
            with self._lock:
                log_debug("Polling Twitter now")
                if self._twitter_api:
                    urls = []
                    for account_name in self._screen_names:
                        try:
                            tweets = self._twitter_api.GetUserTimeline(screen_name=account_name)
                            if len(tweets):
                                try:
                                    for media in tweets[0].media:
                                        urls.append((media["media_url"],tweets[0].text))
                                except:
                                    item = tweets[0].AsDict()
                                    urls = [(url,item['text']) for url in item['text'].split(" ") if url.startswith("http")]   
                            log_debug("Twitter: from %s extracted URLs: %s"%(str(account_name),str(urls)))  
                            
                            #for u in urls:
                            u = urls[0]
                            get_server().call("HELO_REMOTE_PIC %s %s:%s"%(u[0],account_name,u[1]))
                        except:
                            log_exception("Twitter: Error while accessing twitter timeline of user ",account_name)

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
        self.stopEvent.set()
        #TODO: join thread
        iface_called_plugin.deactivate(self)
        
    def authenticate(self,oldv=None,newv=None):
        self.dthread.authenticate(self.options["key"],self.options["secret"],self.options["at_key"],self.options["at_secret"])
    
    def reset_timer(self,oldv=None,newv=None):
        self.dthread.set_polling_time(self.options["polling_time"])
        
    def set_twitter_pics(self,oldv=None,newv=None):
        screen_names = [self.options["twitter_pics"]]
        self.dthread.set_screen_names(screen_names)
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        pass

    def process_message(self,msg,addr,member_info):
        pass        
