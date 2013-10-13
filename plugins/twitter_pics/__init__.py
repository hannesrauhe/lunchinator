from lunchinator.iface_plugins import iface_gui_plugin
import subprocess, sys, ctypes
from lunchinator import get_server, log_exception, log_warning, get_settings, convert_string, log_error, log_info, log_debug
from lunchinator.download_thread import DownloadThread
from lunchinator.utilities import displayNotification, getValidQtParent

import urllib2, tempfile, json, time, twitter, contextlib
from get_access_token import get_access_token

from PyQt4.QtCore import QThread, pyqtSignal

class TwitterDownloadThread(QThread):
    success = pyqtSignal(QThread, tuple)
    unchanged = pyqtSignal(QThread, tuple)
    error = pyqtSignal(QThread, tuple)
    
    def __init__(self, parent, twitter_api, screen_name, target, pic_url):
        super(TwitterDownloadThread, self).__init__(parent)
        self.twitter_api = twitter_api
        self.screen_name = screen_name
        self.target = target
        self.pic_url = None

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
        
        if len(urls) and urls[0]!=self.pic_url:
            self.pic_url=urls[0]
            try:
                with contextlib.closing(urllib2.urlopen(self.pic_url[0])) as u:
                    self.target.seek(0)
                    self.target.truncate()
                    self.target.write(u.read())
                    self.success.emit(self, self.pic_url)
            except:
                log_exception("Error while downloading %s"%str(self.pic_url))
                self.error.emit(self, self.pic_url)
        else:
            self.unchanged.emit(self, self.pic_url)

class twitter_pics(iface_gui_plugin):
    def __init__(self):
        super(twitter_pics, self).__init__()
        self.options = [(("twitter_user","Twitter User"),"HistoricalPics"),
                        (("key","API Key"),""),
                        (("secret","API Secret"),""),
                        (("at_key","Access Token Key"),""),
                        (("at_secret","Access Token Secret"),"")]
        self.localFile = None
        self.pic_url = ("","")
        
    def activate(self):        
        iface_gui_plugin.activate(self)
        self.localFile = tempfile.NamedTemporaryFile()
        self.forceDownload = False
        if len(self.options["key"]) and len(self.options["secret"]) and len(self.options["at_key"]) and len(self.options["at_secret"]):
            self.twitter_api = twitter.Api(consumer_key=self.options["key"],
                         consumer_secret=self.options["secret"],
                         access_token_key=self.options["at_key"],
                         access_token_secret=self.options["at_secret"],
                         debugHTTP=False)
            self.download_pic(True)
        else:
            log_error("Twitter Pics: provide keys and secrets in settings")
    
    def deactivate(self):    
        if self.localFile:    
            self.localFile.close()
        iface_gui_plugin.deactivate(self)
            
    def create_widget(self, parent):
        from lunchinator.resizing_image_label import ResizingImageLabel
        from PyQt4.QtCore import QSize
        
        super(twitter_pics, self).create_widget(parent)
        self.imageLabel = ResizingImageLabel(parent, True, QSize(400,400))
        return self.imageLabel

    def process_message(self,msg,addr,member_info):
        pass
    
    def errorDownloadingPicture(self, thread, url):
        log_error("Error downloading picture from url %s" % str(url))
        thread.deleteLater()
        
    def downloadedPicture(self, _thread, pic_url):
        self.pic_url = pic_url
        self.localFile.flush()
        displayNotification("Twitter", pic_url[1], self.localFile.name)
        self.imageLabel.setImage(self.localFile.name) 
        self.imageLabel.setToolTip(pic_url[1])  
        
    def foundOldPicture(self, _thread, pic_url):
        log_debug("Twitter Pics: no new picture found")          
          
    def download_pic(self,force=False):
        thread = TwitterDownloadThread(getValidQtParent(), self.twitter_api, self.options['twitter_user'], self.localFile, self.pic_url)
        thread.success.connect(self.downloadedPicture)
        thread.error.connect(self.errorDownloadingPicture)
        thread.unchanged.connect(self.foundOldPicture)
        thread.finished.connect(thread.deleteLater)
        thread.start()
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        pass
