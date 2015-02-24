import subprocess, sys, ctypes, logging
import tempfile, json, time, contextlib, csv
from cStringIO import StringIO
from threading import Thread,Event,Lock

from lunchinator.logging_mutex import loggingMutex
from lunchinator.plugin import iface_gui_plugin, db_for_plugin_iface
from lunchinator import get_server, get_settings, convert_string
from twitter_lunch.twitter_thread import TwitterDownloadThread
from twitter_lunch.setup_gui import SetupGui
from twitter_lunch.twitter_sqlite import twitter_sqlite

class twitter_lunch(iface_gui_plugin):
    def __init__(self):
        super(twitter_lunch, self).__init__()
        self.options = [(("key","API Key", self.reset_options),""),
                        (("secret","API Secret", self.reset_options),""),
                        (("at_key","Access Token Key", self.reset_options),""),
                        (("at_secret","Access Token Secret", self.reset_options),""),
                        (("relay_calls","Tweet received lunch calls"),True),
                        (("relay_tweets","Allow remote calls", self.reset_options), False),
                        (("picture_list","Others can add accounts to your picture list"), True),
                        (("polling_time","Polling Time", self.reset_options),60)]
        
        self.add_supported_dbms("SQLite Connection", twitter_sqlite)
        self.dthread = None
        self._twitter_gui = None
        
    def get_displayed_name(self):
        return u"Twitter"
        
    def activate(self):        
        iface_gui_plugin.activate(self)
        self.reset_options()
        
    def reset_options(self, oldv=None, newv=None):
        if self.dthread and self.dthread.isAlive():
            self.dthread.reset_options(self.options)
        else:        
            self.dthread = TwitterDownloadThread(self.logger, self.specialized_db_conn, self.options)        
            self.dthread.start()
    
    def deactivate(self):
        if self.dthread and self.dthread.isAlive():
            self.logger.info("Waiting for Twitter Thread to stop")
            self.dthread.stop()
            self.dthread.join()
            self.logger.info("Twitter thread stopped")
        iface_gui_plugin.deactivate(self)
            
    def process_group_message(self, xmsg, ip, member_info, lunch_call):
        if self.dthread == None or not self.dthread.isAlive():
            return
        
        if lunch_call and self.options["relay_calls"]:            
            message = unicode("Lunchtime: ") + xmsg.getPlainMessage()
            if member_info.has_key(ip):
                message+=u" ("+unicode(member_info[u'name'])+u")"
            self.dthread.post(message)
        
    def process_command(self,xmsg,_,__,___):
        if self.dthread == None or not self.dthread.isAlive():
            return
        
        cmd = xmsg.getCommand()
        value = xmsg.getCommandPayload()
        if cmd.startswith("REQUEST_PIC") and self.options["picture_list"]:
            if cmd=="REQUEST_PIC_TWITTER":
                self.dthread.add_picture_account(value)
                self.logger.debug("Twitter: Now following these streams for pics: %s", str(self.dthread.get_picture_accounts()))
            if self.dthread.get_old_pic_urls().has_key(value):
                self.dthread.announce_pic(value, self.dthread.get_old_pic_urls()[value])
            else:
                for account_name,u in self.dthread.get_old_pic_urls().iteritems():
                    self.dthread.announce_pic(account_name, u)            
            
        elif cmd=="TWITTER_USER":
            self.dthread.add_remote_caller(value)
            self.logger.debug("Twitter: Now accepting remote calls from: %s", str(self.dthread.get_remote_callers()))   
            
    
    def do_tweets(self, cmd):
        for t in self.specialized_db_conn().get_last_tweets():
            print "@%s: %s"%(t[1], t[0])
                     
    def create_widget(self, parent):        
        from safe_connector import SafeConnector
        from twitter_gui import TwitterGui
        sc = SafeConnector()
        self._twitter_gui = TwitterGui(parent, self.logger, 
                                       self.specialized_db_conn(), 
                                       self.dthread.trigger_update,
                                       sc)
        self.dthread.setSafeConn(sc)
        return self._twitter_gui
    
    def destroy_widget(self):
        if self._twitter_gui:
            self._twitter_gui = None
        
