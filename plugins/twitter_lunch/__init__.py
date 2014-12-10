import subprocess, sys, ctypes, logging
import tempfile, json, time, contextlib, csv
from cStringIO import StringIO
from threading import Thread,Event,Lock

from lunchinator.logging_mutex import loggingMutex
from lunchinator.plugin import iface_gui_plugin, db_for_plugin_iface
from lunchinator import get_server, get_settings, convert_string
from twitter_lunch.twitter_thread import TwitterDownloadThread
from twitter_lunch.setup_gui import SetupGui

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
        self._twitter_gui = None
        
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
            
    
    def do_tweets(self, cmd):
        for t in self.specialized_db_conn().get_last_tweets():
            print "@%s: %s"%(t[1], t[0])
                     
    def create_widget(self, parent):
        if not (self.options["key"] and self.options["secret"] and self.options["at_key"] and self.options["at_secret"]):
            return SetupGui(parent, self.logger)
        
        from twitter_gui import TwitterGui
        self._twitter_gui = TwitterGui(parent, None, self.logger, self.specialized_db_conn())
        self._twitter_gui.start()
        return self._twitter_gui
    
    def destroy_widget(self):
        if self._twitter_gui:
            self._twitter_gui.stop()
            self._twitter_gui = None
        
    
class twitter_sqlite(db_for_plugin_iface):
    messages_schema = "CREATE TABLE twitter_messages (m_id BIGINT PRIMARY KEY, \
            screen_name TEXT, user_image TEXT, create_time INTEGER, message_text TEXT)"
    post_queue_schema = "CREATE TABLE twitter_post_queue (q_id  INTEGER PRIMARY KEY AUTOINCREMENT, \
            message_text TEXT, reply_to BIGINT, create_time INTEGER, m_id BIGINT)"
    version_schema = "CREATE TABLE twitter_version (commit_count INTEGER, migrate_time INTEGER)"
            
    
    def init_db(self):                   
        if not self.dbConn.existsTable("twitter_version"):
            self.dbConn.execute(self.version_schema)
            self.dbConn.execute("INSERT INTO twitter_version(commit_count, migrate_time) VALUES(?, strftime('%s', 'now'))", 1959)
        if not self.dbConn.existsTable("twitter_messages"):
            self.dbConn.execute(self.messages_schema)
        if not self.dbConn.existsTable("twitter_post_queue"):
            self.dbConn.execute(self.post_queue_schema)
        
    def insert_message(self, tweetAsStatus):
        created_at = tweetAsStatus.GetCreatedAtInSeconds()
        tweet = tweetAsStatus.AsDict()
        self.dbConn.execute("INSERT INTO twitter_messages(m_id, screen_name, user_image, create_time, message_text) \
                            VALUES(?, ?, ?, ?, ?)", tweet["id"], tweet["user"]["screen_name"], 
                            tweet["user"]["profile_image_url"], int(created_at), tweet["text"])
        
    def insert_post_queue(self, text):
        self.dbConn.execute("INSERT INTO twitter_post_queue(message_text) VALUES(?)", text)        
    
    """return last num tweets (only if anything has happened since min_m_id)"""
    def get_last_tweets(self, min_m_id = 0, num = 20):   
        if min_m_id != 0:
            tmp = self.dbConn.query("SELECT m_id \
                                    FROM twitter_messages \
                                    WHERE m_id>?", min_m_id)
            if len(tmp)==0:
                return []
          
        r = self.dbConn.query("SELECT message_text, screen_name, user_image, create_time, m_id \
                                FROM twitter_messages \
                                ORDER BY m_id DESC LIMIT ?", num)
        return r
    
    def get_max_id(self):    
        r = self.dbConn.query("SELECT MAX(m_id) FROM twitter_messages")
        if not r:
            return 0
        return r[0][0]
