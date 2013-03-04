
from iface_plugins import *
from yapsy.PluginManager import PluginManagerSingleton
from twitter import *

import os,sys

class twitter_status(iface_called_plugin):
    twitter = None
    ls = None
    
    def __init__(self):
        super(twitter_status, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        
    def activate(self):
        iface_called_plugin.activate(self)
        
        if self.hasConfigOption("key") and self.hasConfigOption("secret"):
            try:
                MY_TWITTER_CREDS = os.path.expanduser('~/.lunchinator/twitter_credentials')
                if not os.path.exists(MY_TWITTER_CREDS):
                    oauth_dance("Lunchinator", self.getConfigOption("key") ,self.getConfigOption("secret"),
                                MY_TWITTER_CREDS)
                
                oauth_token, oauth_secret = read_token_file(MY_TWITTER_CREDS)
                
                self.twitter = Twitter(auth=OAuth(
                    oauth_token, oauth_secret, self.getConfigOption("key") ,self.getConfigOption("secret") ))
            except:
                print "Authentication with twitter was unsuccessful. The plugin will not work.",sys.exc_info()[0]
        else:
            self.setConfigOption("key","KEY_HERE")
            self.setConfigOption("secret","SECRET_HERE")
            print "fill in your application key and secret to settings.cfg - I added some placeholders there"
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        pass
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        if self.twitter:
            statustxt = "Lunchtime!"
            if member_info and member_info.has_key("name"):
                statustxt += " "+member_info["name"]
            self.twitter.statuses.update(status=statustxt[:140])
        else:
            print "twitter integration did not work",sys.exc_info()[0]
    
    def process_event(self,cmd,value,ip,member_info):
        pass