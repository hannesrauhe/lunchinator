from lunchinator import get_server, get_settings, convert_string
from twitter_lunch.twitter_sqlite import twitter_sqlite

import subprocess, sys, ctypes, logging
import tempfile, json, time, contextlib, csv
from cStringIO import StringIO

from threading import Thread,Event,Lock
from lunchinator.logging_mutex import loggingMutex

class TwitterDownloadThread(Thread):
    PICTURE_LIST_NAME = "Pictures"
    REMOTE_PIC_CATEGORY = "Twitter"
    
    def __init__(self, logger, get_db_conn_func, options):
        super(TwitterDownloadThread, self).__init__()
        self.logger = logger
        self._get_db_conn = get_db_conn_func
        self._options = options
        
        self._safe_conn = None        
        self._twitter_api = None
        self._stop_event = Event()
        self._wait_event = Event()
        self._lock = loggingMutex("twitter download thread", logging=get_settings().get_verbose())
        
        self._own_screen_name = ""
        self._old_pic_urls = {}
        self._since_ids = {}
        self._mentions_since_id = 0
        self._remote_callers = []
        self._friends = []
                    
    def add_picture_account(self,s):
        with self._lock:
            if len(s) and not s.upper() in [x.upper() for x in self.get_picture_accounts()]:
                self._get_db_conn().add_user_to_list(s, self.PICTURE_LIST_NAME)
                if not self._old_pic_urls.has_key(s):
                    self._old_pic_urls[s]=("","")
                if not self._since_ids.has_key(s):
                    self._since_ids[s]=0
                   
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
            
    def announce_pic(self,account_name,url_text_tuple, peerIDs = []):        
        if len(url_text_tuple[0]):
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter = ' ', quotechar = '"')
                writer.writerow([url_text_tuple[0].encode("utf-8"), 
                                 url_text_tuple[1].encode("utf-8"), account_name])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue(), peerIDs)
                    
    def get_old_pic_urls(self):
        return self._old_pic_urls
    
    def get_remote_callers(self):
        return self._remote_callers
    
    def get_picture_accounts(self):
        return self._get_db_conn().get_users_from_list(self.PICTURE_LIST_NAME)
    
    def post(self,message):
        if self._twitter_api == None:
            self.logger.error("Twitter: cannot post - not authenticated")
            return False
        
        try:
            self._twitter_api.PostUpdate(message[0:140])
        except:
            self.logger.exception("Twitter: was not able to post %s", message)
        
    def reset_options(self, options): 
        if not (options["key"], options["secret"], options["at_key"], options["at_secret"]) == \
        (self._options["key"], self._options["secret"], self._options["at_key"], self._options["at_secret"]):
            with self._lock:
                self._twitter_api = None          
        self._options = options
        self._wait_event.set()
                
    def run(self):
        import twitter,requests 
        #first give the lunchinator a few seconds to initialize to prevent a warning
        self._wait_event.wait(10)  
        while not self._stop_event.isSet():                 
            self._wait_event.clear()       
            if not self._authenticate():
                self._wait_event.wait(self._polling_time) 
                continue
            
            if self._safe_conn:
                self._safe_conn.emit_twitter_loop_started()
            
            poll_time = self._options["polling_time"]
            self.logger.debug("Polling Twitter now")
            try:
                self._post_update_queue()
                self._get_home_timeline() 
                
                for account_name in self.get_picture_accounts():
                    self._get_pics_from_account(account_name)
                if self._options["relay_tweets"]:
                    self._find_remote_calls() 
            except twitter.TwitterError as t:
                self.logger.warning("Twitter: Rate limit exceeded. Waiting 15 min: %s", str(t))
                poll_time = 60*15
                if self._safe_conn:
                    self._safe_conn.emit_range_limit_exceeded()
            except requests.ConnectionError as e:
                self.logger.warning("Twitter: Connection error. Waiting 15 min: %s", str(e))
                poll_time = 60*15
            except:
                self.logger.exception("Twitter: Unknown error")
            finally:                
                if self._safe_conn:
                    self._safe_conn.emit_twitter_loop_stopped()
                
            #returns None on Python 2.6
            self._wait_event.wait(poll_time)            
        
    def setSafeConn(self, safe_conn):
        self._safe_conn = safe_conn
    
    def stop(self):    
        self._stop_event.set()
        self._wait_event.set()  
        
    def trigger_update(self):
        self._wait_event.set()
            
    def _authenticate(self):
        import twitter
        
        if self._twitter_api != None:
            return True
              
        with self._lock:
            try:
                self._twitter_api = twitter.Api(consumer_key=self._options["key"],
                             consumer_secret=self._options["secret"],
                             access_token_key=self._options["at_key"],
                             access_token_secret=self._options["at_secret"],
                             debugHTTP=False)
                self._mentions_since_id = 0
            except:
                self.logger.exception("Twitter: authentication with twitter failed: check settings")
                self._twitter_api = None
                if self._safe_conn:
                    self._safe_conn.emit_not_authenticated()
                return False
            try:
                self._own_screen_name = self._twitter_api.VerifyCredentials().GetScreenName()
            except:
                self.logger.exception("Twitter: was not able to find my screen_name")
                self._twitter_api = None
                if self._safe_conn:
                    self._safe_conn.emit_not_authenticated()
                return False
            
        return True
                
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
                    return    
                
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
#                         self._twitter_api.PostUpdate(u"@"+s_name+u" Sorry, I do not know you", m.GetId())
                        continue
                    get_server().call("Remote call by @%s: %s"%(s_name,m.GetText()))
                    self._twitter_api.PostUpdate(u"@"+s_name+u" OK, I forwarded your message", m.GetId())
            except twitter.TwitterError as t:
                if t[0][0][u'code']==88:
                    raise
                else:
                    self.logger.error("Twitter: Error while trying to retrieve mentions %s", str(t))   
                
    def _get_home_timeline(self):
        with self._lock:
            self._timeline_since_id = self._get_db_conn().get_max_id()
            tweets = self._twitter_api.GetHomeTimeline(since_id=self._timeline_since_id, count=200)
            if len(tweets)==0:
                self.logger.debug("Twitter: no new tweets in timeline")
                return
            
            for t in tweets:
                self._get_db_conn().insert_message(t)
                
                pic_subtitle = "@" + t.GetUser().GetScreenName() + ": " + t.text
                urls = []
                try:
                    for media in t.media:
                        urls.append((media["media_url"], pic_subtitle))
                except:
                    urls = [(url, pic_subtitle) for url in t.text.split(" ") if url.startswith("http")]  
                    
                for u in urls:
                    self.announce_pic(self.REMOTE_PIC_CATEGORY, u, [get_settings().get_ID()])
                    
        if self._safe_conn:
            self._safe_conn.emit_home_timeline_updated()
            
    def _get_pics_from_account(self,account_name):
        import twitter
        with self._lock:
            try:
                urls = []
                tweets = self._twitter_api.GetUserTimeline(screen_name=account_name, 
                                                           since_id=self._since_ids.get(account_name, 0))
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
                for u in urls:
                    self.announce_pic(account_name, u)
                    self._old_pic_urls[account_name]=u
            except twitter.TwitterError as t:
                if t[0][0][u'code']==88:
                    raise
                else:  
                    self.logger.error("Twitter: Error while trying to retrieve pics from %s: %s", account_name,str(t))
                    
    def _post_update_queue(self):
        import twitter
        posts = self._get_db_conn().get_unprocessed_queue()
        if 0==len(posts):          
            return
        
        with self._lock:
            for post in posts:
                """ 0 - id, 1 - reply-to, 2 -text """
                pstatus = None
                pm_id = -1
                try:
                    if post[1]:
                        self.logger.debug("Posting status %s as reply to %d"%(post[2], post[1]))
                        pstatus = self._twitter_api.PostUpdate(post[2], post[1])
                    else:
                        self.logger.debug("Posting status %s"%(post[2]))
                        pstatus = self._twitter_api.PostUpdate(post[2])
                    pm_id = pstatus.GetId()
                    self._get_db_conn().update_post_queue(post[0], pm_id, pstatus.GetCreatedAtInSeconds())
                except twitter.TwitterError as t:
                    if t[0][0][u'code']==88:
                        raise
                    else:
                        self._get_db_conn().update_post_queue(post[0], -1 * t[0][0][u'code'])
                        self.logger.error("Failed to send tweet \"%s\" \n%s (Error code: %d)\n ",post[2], 
                                          t[0][0]["message"], t[0][0]["code"])
                finally:                    
                    if self._safe_conn:
                        self._safe_conn.emit_update_posted(post[0], pm_id)
                    
                    
                    