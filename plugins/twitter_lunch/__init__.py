from lunchinator.plugin import iface_gui_plugin, db_for_plugin_iface
from lunchinator import get_server, get_settings, convert_string

import subprocess, sys, ctypes, logging
import tempfile, json, time, contextlib, csv
from cStringIO import StringIO

from threading import Thread,Event,Lock
from lunchinator.logging_mutex import loggingMutex
from twitter_lunch.twitter_gui import TwitterGui

class TwitterDownloadThread(Thread):    
    def __init__(self, event, logger, db_conn):
        super(TwitterDownloadThread, self).__init__()
        self.logger = logger
        self._twitter_api = None
        self._own_screen_name = ""
        self._screen_names = []
        self._old_pic_urls = {}
        self._since_ids = {}
        self._stop_event = event
        self._lock = loggingMutex("twitter download thread", logging=get_settings().get_verbose())
        self._polling_time = 60
        self._mentions_since_id = 0
        self._remote_callers = []
        self._friends = []
        self._db_conn = db_conn
            
    def announce_pic(self,account_name,url_text_tuple, peerIDs = []):        
        if len(url_text_tuple[0]):
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter = ' ', quotechar = '"')
                writer.writerow([url_text_tuple[0].encode("utf-8"), url_text_tuple[1].encode("utf-8"), account_name])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue(), peerIDs)
        
    def set_polling_time(self,v):
        self._polling_time = v
                    
    def get_screen_names(self):
        return self._screen_names
                    
    def add_screen_name(self,s):
        with self._lock:
            if len(s) and not s.upper() in [x.upper() for x in self._screen_names]:
                self._screen_names.append(s)
                if not self._old_pic_urls.has_key(s):
                    self._old_pic_urls[s]=("","")
                if not self._since_ids.has_key(s):
                    self._since_ids[s]=0
                    
    def get_remote_callers(self):
        return self._remote_callers
                   
    def add_remote_caller(self,value):
        if len(value)==0:
            return
        
        remote_caller = value[1:] if value[0]=="@" else value
        with self._lock:
            if not remote_caller.upper() in [x.upper() for x in self._remote_callers]:
                self._remote_callers.append(remote_caller)
                
        '''this shoul be done by the twitter thread:
        if not remote_caller.upper() in [x.upper() for x in self._friends]:
            try:
                self._friends = [x.GetScreenName() for x in self._twitter_api.GetFriends()]
                self.logger.debug("Twitter: my Friends %s", self._friends)
            except:
                self.logger.exception("Twitter: was not able to fetch my friends")
            
            try:
                self._twitter_api.CreateFriendship(screen_name=remote_caller)
                self._friends.append(unicode(remote_caller))
                self.logger.debug("Twitter: now following %s", remote_caller)
            except:
                self.logger.exception("Twitter: cannot follow %s", remote_caller)
        '''
                
                
    def get_old_pic_urls(self):
        return self._old_pic_urls
            
    def authenticate(self,key,secret,at_key,at_secret):
        import twitter
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
                    self.logger.exception("Twitter: authentication with twitter failed: check settings")
                    self._twitter_api = None
                    return False
                try:
                    self._own_screen_name = self._twitter_api.VerifyCredentials().GetScreenName()
                except:
                    self.logger.exception("Twitter: was not able to find my screen_name")
                    self._twitter_api = None
                    return False                
                    
            else:
                self.logger.error("Twitter: provide keys and secrets in settings")
                self._twitter_api = None
                return False
            
    def post(self,message):
        if self._twitter_api == None:
            self.logger.error("Twitter: cannot post - not authenticated")
            return False
        
        try:
            self._twitter_api.PostUpdate(message[0:140])
        except:
            self.logger.exception("Twitter: was not able to post %s", message)
                
    def _get_home_timeline(self):
        import twitter
        with self._lock:
            self._timeline_since_id = self._db_conn.get_max_id()
            tweets = self._twitter_api.GetHomeTimeline(200, self._timeline_since_id)
            if len(tweets)==0:
                self.logger.debug("Twitter: no new tweets in timeline")
            for t in tweets:
                self._db_conn.insert_message(t)
                
                urls = []
                try:
                    for media in t.media:
                        urls.append((media["media_url"],t.text))
                except:
                    item = t.AsDict()
                    urls = [(url,item['text']) for url in item['text'].split(" ") if url.startswith("http")]  
                    
                for u in urls:
                    self.announce_pic("timeline", u, [get_settings().get_ID()])
                

    def _get_pics_from_account(self,account_name):
        import twitter
        with self._lock:
            try:
                urls = []
                tweets = self._twitter_api.GetUserTimeline(screen_name=account_name,since_id=self._since_ids[account_name])
                if 0==len(tweets):
                    self.logger.debug("Twitter: no new tweets from %s since %s", str(account_name), self._since_ids[account_name])
                    return
                
                self._since_ids[account_name] = tweets[0].GetId()
                
                try:
                    for media in tweets[0].media:
                        urls.append((media["media_url"],tweets[0].text))
                except:
                    item = tweets[0].AsDict()
                    urls = [(url,item['text']) for url in item['text'].split(" ") if url.startswith("http")]  
                     
                self.logger.debug("Twitter: from %s extracted URLs: %s", str(account_name),str(urls))  
                if len(urls):
                #for u in urls:
                    self.announce_pic(account_name, urls[0])
                    self._old_pic_urls[account_name]=urls[0]
            except twitter.TwitterError as t:
                if t[0][0][u'code']==88:
                    raise
                else:  
                    self.logger.error("Twitter: Error while trying to retrieve pics from %s: %s", account_name,str(t))
                
    def _find_remote_calls(self):
        import twitter
        get_server().call("HELO_TWITTER_REMOTE %s"%self._own_screen_name)          
        with self._lock:      
            try:  
                if 0 == self._mentions_since_id:
                    #determine the start
                    ments = self._twitter_api.GetMentions(count=1)
                    if len(ments):
                        self._mentions_since_id = ments[0].GetId()
                    else:
                        self._mentions_since_id = 1
                    self.logger.debug("Twitter: Starting with mentions ID %s", self._mentions_since_id)            
                
                ments = self._twitter_api.GetMentions(since_id=self._mentions_since_id)
                if 0==len(ments):
                    self.logger.debug("Twitter: Nobody mentioned me since %s", self._mentions_since_id)
                    return
                self._mentions_since_id = ments[0].GetId()
                for m in ments:
                    self.logger.debug("Twitter: I was mentioned: %s %s", m.GetUser(), m.GetText())
                    s_name = m.GetUser().GetScreenName()
                    if s_name not in self._remote_callers:
                        self.logger.debug("Twitter: I do not know him")
                        self._twitter_api.PostUpdate(u"@"+s_name+u" Sorry, I do not know you", m.GetId())
                        continue
                    get_server().call("Remote call by @%s: %s"%(s_name,m.GetText()))
                    self._twitter_api.PostUpdate(u"@"+s_name+u" OK, I forwarded your message", m.GetId())
            except twitter.TwitterError as t:
                if t[0][0][u'code']==88:
                    raise
                else:
                    self.logger.error("Twitter: Error while trying to retrieve mentions %s", str(t))   
        
                
    def run(self):
        import twitter,requests 
        #first give the lunchinator a few seconds to initialize to prevent a warning
        self._stop_event.wait(10)  
        while not self._stop_event.isSet():            
            if None==self._twitter_api:
                self._stop_event.wait(self._polling_time) 
                continue
            
            poll_time = self._polling_time
            self.logger.debug("Polling Twitter now")
            try:
                for account_name in self._screen_names:
                    self._get_pics_from_account(account_name)
                
                self._find_remote_calls()
                self._get_home_timeline()  
            except twitter.TwitterError as t:
                self.logger.warning("Twitter: Rate limit exceeded. Waiting 15 min: %s", str(t))
                poll_time = 60*15
            except requests.ConnectionError as e:
                self.logger.warning("Twitter: Connection error. Waiting 15 min: %s", str(e))
                poll_time = 60*15
            except:
                self.logger.exception("Twitter: Unknown error")
                
            #returns None on Python 2.6
            self._stop_event.wait(poll_time)      
        

class twitter_lunch(iface_gui_plugin):
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
        self.add_supported_dbms("SQLite Connection", twitter_sqlite)
        
    def get_displayed_name(self):
        return u"Twitter"
        
    def activate(self):        
        iface_gui_plugin.activate(self)
        
        self.dthread = TwitterDownloadThread(self.stopEvent, self.logger, self.specialized_db_conn())
        self.authenticate()
        self.set_twitter_pics()
        self.reset_timer()
        
        self.dthread.start()
    
    def deactivate(self):
        self.logger.info("Waiting for Twitter Thread to stop")
        self.stopEvent.set()
        self.dthread.join()
        self.logger.info("Twitter thread stopped")
        iface_gui_plugin.deactivate(self)
        
    def authenticate(self,oldv=None,newv=None):
        self.dthread.authenticate(self.options["key"],self.options["secret"],self.options["at_key"],self.options["at_secret"])
    
    def reset_timer(self,oldv=None,newv=None):
        self.dthread.set_polling_time(self.options["polling_time"])
        
    def set_twitter_pics(self,oldv=None,newv=None):
        for sname in self.options["twitter_pics"].split(";;"):
            self.dthread.add_screen_name(sname)
            
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        if lunch_call:
            message = unicode("Lunchtime: ") + xmsg.getPlainMessage()
            if member_info.has_key(ip):
                message+=u" ("+unicode(member_info[u'name'])+u")"
            self.dthread.post(message)
        
    def process_command(self,xmsg,_,__,___):
        cmd = xmsg.getCommand()
        value = xmsg.getCommandPayload()
        if cmd.startswith("REQUEST_PIC"):
            if cmd=="REQUEST_PIC_TWITTER":
                self.dthread.add_screen_name(value)
                self.logger.debug("Twitter: Now following these streams for pics: %s", str(self.dthread.get_screen_names()))
                self.set_option("twitter_pics",";;".join(self.dthread.get_screen_names()))
            if self.dthread.get_old_pic_urls().has_key(value):
                self.dthread.announce_pic(value, self.dthread.get_old_pic_urls()[value])
            else:
                for account_name,u in self.dthread.get_old_pic_urls().iteritems():
                    self.dthread.announce_pic(account_name, u)            
            
        elif cmd=="TWITTER_USER":
            self.dthread.add_remote_caller(value)
            self.logger.debug("Twitter: Now accepting remote calls from: %s", str(self.dthread.get_remote_callers()))   
                     
    def create_widget(self, parent):
        if not (self.options["key"] and self.options["secret"] and self.options["at_key"] and self.options["at_secret"]):
            from PyQt4.QtGui import QLabel
            from PyQt4.QtCore import Qt
            return QLabel("Please make sure that secrets and keys in settings are correct")
        from twitter_gui import TwitterGui
        return TwitterGui(None, None, self.logger, self.specialized_db_conn())
    
class twitter_sqlite(db_for_plugin_iface):
    messages_schema = "CREATE TABLE twitter_messages (m_id BIGINT PRIMARY KEY, \
            screen_name TEXT, user_image TEXT, create_time INTEGER, message_text TEXT)"
    version_schema = "CREATE TABLE twitter_version (commit_count INTEGER, migrate_time INTEGER)"
            
    
    def init_db(self):                   
        if not self.dbConn.existsTable("twitter_version"):
            self.dbConn.execute(self.version_schema)
            self.dbConn.execute("INSERT INTO twitter_version(commit_count, migrate_time) VALUES(?, strftime('%s', 'now'))", 1959)
        if not self.dbConn.existsTable("twitter_messages"):
            self.dbConn.execute(self.messages_schema)
        
    def insert_message(self, tweetAsStatus):
        created_at = tweetAsStatus.GetCreatedAtInSeconds()
        tweet = tweetAsStatus.AsDict()
        self.dbConn.execute("INSERT INTO twitter_messages(m_id, screen_name, user_image, create_time, message_text) \
                            VALUES(?, ?, ?, ?, ?)", tweet["id"], tweet["user"]["screen_name"], 
                            tweet["user"]["profile_image_url"], int(created_at), tweet["text"])
    
    def get_last_tweets(self, num = 20):    
        r = self.dbConn.query("SELECT message_text, screen_name, user_image, create_time, m_id FROM twitter_messages ORDER BY m_id DESC LIMIT ?", num)
        return r
    
    def get_max_id(self):    
        r = self.dbConn.query("SELECT MAX(m_id) FROM twitter_messages")
        if not r:
            return 0
        return r[0][0]
