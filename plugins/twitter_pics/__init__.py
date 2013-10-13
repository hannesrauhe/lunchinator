from lunchinator.iface_plugins import iface_gui_plugin
import subprocess, sys, ctypes
from lunchinator import get_server, log_exception, log_warning, get_settings, convert_string, log_error, log_info, log_debug
from lunchinator.download_thread import DownloadThread
from lunchinator.utilities import displayNotification, getValidQtParent

import urllib2, tempfile, json, time, twitter, contextlib

from PyQt4.QtCore import QThread, pyqtSignal, QTimer

class TwitterDownloadThread(QThread):
    success = pyqtSignal(QThread, tuple)
    unchanged = pyqtSignal(QThread, tuple)
    error = pyqtSignal(QThread, tuple)
    
    def __init__(self, parent, twitter_api, screen_name, target, old_pic_url):
        super(TwitterDownloadThread, self).__init__(parent)
        self.twitter_api = twitter_api
        self.screen_name = screen_name
        self.target = target
        self.old_pic_url = old_pic_url
        
    def run(self):
        urls = []
        try:
            tweets = self.twitter_api.GetUserTimeline(screen_name=self.screen_name)
            if len(tweets):
                try:
                    for media in tweets[0].media:
                        urls.append((media["media_url"],tweets[0].text))
                except:
                    item = tweets[0].AsDict()
                    urls = [(url,item['text']) for url in item['text'].split(" ") if url.startswith("http")]   
            log_debug("Twitter Pics: extracted URLs: %s"%str(urls))  
        except:
            log_exception("Twitter Pics: Error while accessing twitter")  
            self.error.emit(self, "Twitter")
            return       
        
        if len(urls) and urls[0]!=self.old_pic_url:
            try:
                with contextlib.closing(urllib2.urlopen(urls[0][0])) as u:
                    self.target.seek(0)
                    self.target.truncate()
                    self.target.write(u.read())
                    self.success.emit(self, urls[0])
            except:
                log_exception("Error while downloading %s"%str(urls[0]))
                self.error.emit(self, urls[0])
        else:    
            self.unchanged.emit(self, self.old_pic_url)

class twitter_pics(iface_gui_plugin):
    def __init__(self):
        super(twitter_pics, self).__init__()
        self.options = [(("twitter_user","Twitter User"),"HistoricalPics"),
                        (("key","API Key"),""),
                        (("secret","API Secret"),""),
                        (("at_key","Access Token Key"),""),
                        (("at_secret","Access Token Secret", self.authenticate),""),
                        (("polling_time","Polling Time", self.reset_timer),60)]
        self.localFile = None
        self.old_pic_url = ("","")
        self.timer = None
        self.twitter_api = None
        
    def activate(self):        
        iface_gui_plugin.activate(self)
        self.localFile = tempfile.NamedTemporaryFile()
        self.forceDownload = False
        self.authenticate()
    
    def deactivate(self):    
        if self.localFile:    
            self.localFile.close()
        iface_gui_plugin.deactivate(self)
            
    def create_widget(self, parent):
        from lunchinator.resizing_image_label import ResizingImageLabel
        from PyQt4.QtCore import QSize
        
        super(twitter_pics, self).create_widget(parent)
        self.imageLabel = ResizingImageLabel(parent, True, QSize(400,400))
        self.timer = QTimer(self.imageLabel)
        self.timer.timeout.connect(self.download_pic)
        self.timer.setSingleShot(False)
        self.timer.start(self.options["polling_time"]*1000)
        return self.imageLabel
    
    def authenticate(self,old_v=None,new_v=None):
        if len(self.options["key"]) and len(self.options["secret"]) and len(self.options["at_key"]) and len(self.options["at_secret"]):
            try:
                self.twitter_api = twitter.Api(consumer_key=self.options["key"],
                             consumer_secret=self.options["secret"],
                             access_token_key=self.options["at_key"],
                             access_token_secret=self.options["at_secret"],
                             debugHTTP=False)
            except:
                log_exception("Twitter Pics: authentication with twitter failed: check settings")
            self.download_pic()
        else:
            log_error("Twitter Pics: provide keys and secrets in settings")
            
    def reset_timer(self,old_v=None,new_v=None):
        self.timer.stop()
        self.timer.start(self.options["polling_time"]*1000)
          
    def download_pic(self):
        if self.twitter_api:
            thread = TwitterDownloadThread(getValidQtParent(), self.twitter_api, self.options['twitter_user'], self.localFile, self.old_pic_url)
            thread.success.connect(self.downloadedPicture)
            thread.error.connect(self.errorDownloadingPicture)
            thread.unchanged.connect(self.foundOldPicture)
            thread.finished.connect(thread.deleteLater)
            thread.start()
    
    def errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % str(url))
        thread.deleteLater()
        
    def downloadedPicture(self, _thread, pic_url):
        self.old_pic_url = pic_url
        self.localFile.flush()
        displayNotification("Twitter", pic_url[1], self.localFile.name)
        self.imageLabel.setImage(self.localFile.name) 
        self.imageLabel.setToolTip(pic_url[1])  
        
    def foundOldPicture(self, _thread, pic_url):
        log_debug("Twitter Pics: no new picture found")  
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        pass

    def process_message(self,msg,addr,member_info):
        pass        
