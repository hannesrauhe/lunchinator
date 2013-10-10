from lunchinator.iface_plugins import iface_called_plugin
from twitter import *
from lunchinator import get_server, log_info, log_warning, log_error, log_exception, log_debug

import os,sys,time,pprint

class twitter_status(iface_called_plugin):
    twitter = None
    def __init__(self):
        super(twitter_status, self).__init__()
        self.options = {"key":"","secret":"","twitter_account":"","polling_time":30}
        self.last_time=0
        self.last_since_id=0
        self.other_twitter_users={}
        self.remote_account = ""
        self.remote_user = ""
        self.is_remote_account = False
        
    def activate(self):
        iface_called_plugin.activate(self)
        
        if len(self.options["key"]) and len(self.options["secret"]):
            try:
                MY_TWITTER_CREDS = os.path.expanduser('~/.lunchinator/twitter_credentials')
                if not os.path.exists(MY_TWITTER_CREDS):
                    oauth_dance("Lunchinator", self.getConfigOption("key") ,self.getConfigOption("secret"),
                                MY_TWITTER_CREDS)
                
                oauth_token, oauth_secret = read_token_file(MY_TWITTER_CREDS)
                
                self.twitter = Twitter(auth=OAuth(
                    oauth_token, oauth_secret, self.getConfigOption("key") ,self.getConfigOption("secret") ))
                
                self.last_time = time.time()
                self.is_remote_account = True
                self.post_update("I am up and running at %s!"%time.asctime())
                get_server().call("HELO_TWITTER_REMOTE %s"%self.remote_account)
            except:
                self.is_remote_account = False
                self.twitter = None
                log_exception("Authentication with twitter was unsuccessful. Check your key and secret. %s"%str(sys.exc_info()))
                
            self.get_mentions()
        else:
            self.is_remote_account = False
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def post_update(self,msg):
        if self.twitter:        
            try:
                log_info("Twitter: posting status: "%msg)
                log_exception("I do not post now, here is the stacktrace:")
#                status = self.twitter.statuses.update(status=msg[:140])
#                self.remote_account="@"+status[u'user'][u'screen_name']
            except:
                log_exception("Twitter: could not post status %s"%msg)
        
    def get_mentions(self):   
        if self.twitter:
            log_debug("Twitter: I am trying to get mentions now, last since id is: %d"%self.last_since_id)
            try:                
                #for when I'm bored -> implementing remote calls via twitter
                ments= []
                if self.last_since_id:
                    ments = self.twitter.statuses.mentions_timeline(since_id=self.last_since_id)
                else:
                    ments = self.twitter.statuses.mentions_timeline()
                    
                if len(ments):
                    self.last_since_id = ments[0]['id']
                    
                log_debug("Twitter: I fetched mentions, last since id is: %d"%self.last_since_id)
                return ments
            except:
                self.last_since_id = 0
                log_exception("Could not retrieve mentions from your timeline. %s"%str(sys.exc_info()))
        return []
    
    def follow(self,screen_name):
        if self.twitter:
            log_debug("Twitter: I'm trying to follow %s now"%screen_name)
#                try:
#                    self.twitter.friendship.create(screen_name=screen_name)
#                except:
#                    log_exception("Unable to follow %s: %s"%(screen_name,str(sys.exc_info())))
        
    def process_message(self,msg,addr,member_info):
        pass
                
    def process_lunch_call(self,_,__,member_info):
        if self.is_remote_account:
            statustxt = "Lunchtime!"
            if member_info and member_info.has_key("name"):
                statustxt += " "+member_info["name"]
            self.post_update(statustxt)
    
    def process_event(self,cmd,value,ip,member_info):
        if cmd=="HELO_TWITTER_USER":
            screen_name = value[1:] if value[0]=="@" else value
            if not self.other_twitter_users.has_key(ip) or self.other_twitter_users[ip]!=screen_name:
                self.other_twitter_users[ip]=screen_name
                self.follow(screen_name)
        elif (not self.is_remote_account) and cmd=="HELO_TWITTER_REMOTE":
            self.remote_account = value
            self.remote_user = member_info["name"] if member_info.has_key("name") else ip
                
            if len(self.options["twitter_account"]):
                get_server().call("HELO_TWITTER_USER %s"%(self.options["twitter_account"]),client=ip)
            else:
                log_warning("No Twitter Account given - Remote Calls won't work")
                
        
        if self.is_remote_account and (time.time()-self.last_time) > (60*self.options["polling_time"]):
            self.last_time=time.time()
            get_server().call("HELO_TWITTER_REMOTE %s"%self.remote_account)
            ments = self.get_mentions()
            if len(ments):                
                log_debug("Twitter: I found new mentions -> I will send a call")
                for ment in ments:
                    tweet_user = ment['user']["screen_name"]
                    tweet_text = ment['text'][len(self.remote_account):]
                    log_debug("Twitter: Mention was: %s from %s"%(tweet_text,tweet_user))

                    reply = ""
                    if tweet_user in self.other_twitter_users.values():
                        if "lunch" in tweet_text:
                            reply = "OK, @%s, I called for lunch"%(tweet_user)
                        else:
                            reply = "OK, @%s, I sent your message around"%(tweet_user)
                        get_server().call("Remote call by %s: %s"%(tweet_user,tweet_text))
                    else:
                        reply = "Sorry, @%s, you're not authorized to call"%(tweet_user)
                    self.post_update(reply)
            
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout, QComboBox, QSpinBox, QLineEdit, QCheckBox
        from PyQt4.QtCore import Qt
        widget = QWidget(parent)
        w = super(twitter_status, self).create_options_widget(widget)
        layout = QVBoxLayout(widget)
        if len(self.options["twitter_account"]):
            if len(self.remote_account)==0:
                msg = "Nobody in your network has configured a remote account - remote calls not possible"
            else:
                msg = "Mention %s in a tweet to trigger a remote call from %s"%(self.remote_account,self.remote_user)
        else:
            msg = "Fill in your twitter account to allow remote lunch calls from it"
        
        layout.addWidget(QLabel(msg, widget))
        if self.is_remote_account:
            layout.addWidget(QLabel("Following users can trigger remote calls: %s"%(", ".join(self.other_twitter_users.values())), widget))
        layout.addWidget(w)
        return widget
            
