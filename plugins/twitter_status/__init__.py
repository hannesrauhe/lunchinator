from lunchinator.iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
from twitter import *

import os,sys,time,pprint

class twitter_status(iface_called_plugin):
    twitter = None
    ls = None
    
    def __init__(self):
        super(twitter_status, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        self.options = {"key":"","secret":"","twitter_account":""}
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
                #for when I'm bored -> implementing remote calls via twitter
#                ments = self.twitter.statuses.mentions_timeline()
#                if len(ments):
#                    self.last_since_id = ments[0].id_str
#                    pp = pprint.PrettyPrinter()
#                    pp.pprint(ments)
#                self.last_since_id
                self.last_time = time.time()
                self.is_remote_account = True
                self.remote_account="@lunchinator"
                self.ls.call("HELO_TWITTER_REMOTE %s"%self.remote_account)
            except:
                self.is_remote_account = False
                self.logger.error("Authentication with twitter was unsuccessful. Check your key and secret.",sys.exc_info()[0])
        else:
            self.is_remote_account = False
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
#        if (time.time()-self.last_time) > (60*1):
#            self.twitter.statuses.mentions_timeline()
            
    def process_lunch_call(self,msg,ip,member_info):
        if self.twitter:
            statustxt = "Lunchtime!"
            if member_info and member_info.has_key("name"):
                statustxt += " "+member_info["name"]
            self.logger.info("pushing to twitter: %s"%statustxt)
            self.twitter.statuses.update(status=statustxt[:140])
        else:
            self.logger.error("sending status to twitter did not work: %s"%str(sys.exc_info()))
    
    def process_event(self,cmd,value,ip,member_info):
        if cmd=="HELO_TWITTER_USER":
            self.other_twitter_users[ip]=value
        elif cmd=="HELO_TWITTER_REMOTE":
            self.remote_account = value
            self.remote_user = member_info["name"] if member_info.has_key("name") else ip
                
            if len(self.options["twitter_account"]):
                self.ls.call("HELO_TWITTER_USER %s"%(self.options["twitter_account"]))
            else:
                self.logger.warning("No Twitter Account given - Remote Calls won't work")
                
        
        if self.is_remote_account and (time.time()-self.last_time) > (60*5):
            self.ls.call("HELO_TWITTER_REMOTE %s"%self.remote_account)
            
    def create_options_widget(self):
        import gtk
        w = super(twitter_status, self).create_options_widget()
        box = gtk.VBox()
        if len(self.options["twitter_account"]):
            if len(self.remote_account)==0:
                msg = "Nobody in your network has configured a remote account - remote calls not possible"
            else:
                msg = "Mention %s in a tweet with the word 'lunch' in it to trigger a remote call from %s"%(self.remote_account,self.remote_user)
        else:
            msg = "Fill in your twitter account to allow remote lunch calls from it"
        
        box.pack_start(gtk.Label(msg), False, True, 10)
        if self.is_remote_account:
            box.pack_start(gtk.Label("Following users can trigger remote calls: %s"%(", ".join(self.other_twitter_users.values()))), False, True, 10)            
        box.pack_start(w, False, True, 10)
        return box
            
