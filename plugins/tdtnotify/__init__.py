from lunchinator.iface_plugins import iface_called_plugin
import subprocess, sys, ctypes
from lunchinator import get_server, log_exception, log_warning, get_settings, convert_string, log_error
from lunchinator.download_thread import DownloadThread
from lunchinator.utilities import displayNotification, getValidQtParent
from cStringIO import StringIO

import urllib2, tempfile, json, time, contextlib, csv

class tdtnotify(iface_called_plugin):
    def __init__(self):
        super(tdtnotify, self).__init__()
        self.options = {"icon_file":get_settings().get_resource("images", "mini_breakfast.png"),
                        "blog_name":"tittendestages",
                        "trigger_word":"",
                        "polling_time":30}
        self.last_time=0
        self.rotate_counter=5
        self.pic_url = ""
        self.localFile = None
        self.forceDownload = False
        self.imageLabel = None
        
    def activate(self):        
        iface_called_plugin.activate(self)
        self.last_time=0
        self.rotate_counter=0
        self.pic_url = ""
    
    def deactivate(self):        
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        if cmd=="HELO_TDTNOTIFY_NEW_PIC" or (time.time()-self.last_time) > (60*self.options["polling_time"]):            
            self.last_time = time.time()
            if not cmd=="HELO_TDTNOTIFY_NEW_PIC":
                get_server().call("HELO_TDTNOTIFY_POLL "+str(self.options["polling_time"]))
                
            self.forceDownload = value=="force"      
            try:
                getValidQtParent()
            except:
                log_warning("TDT Notify does not work without QT")
                return
            downloadThread = DownloadThread(getValidQtParent(), "http://api.tumblr.com/v2/blog/"+self.options['blog_name']+".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY")
            downloadThread.success.connect(self.downloadedJSON)
            downloadThread.error.connect(self.errorDownloadingJSON)
            downloadThread.finished.connect(downloadThread.deleteLater)
            downloadThread.start()
        
    def errorDownloadingJSON(self, thread, url):
        log_error("Error downloading JSON from url %s" % convert_string(url))
        thread.deleteLater()
    
    def downloadedJSON(self, thread, _):
        j = json.loads(thread.getResult())
        #if :
        #    self.rotate_counter = 0
        oldurl = self.pic_url
        self.pic_url = j['response']['posts'][self.rotate_counter]['photos'][0]['original_size']['url']
        if self.forceDownload or oldurl!=self.pic_url:
            get_server().call("HELO_TDTNOTIFY_NEW_PIC "+self.pic_url)
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter = ' ', quotechar = '"')
                writer.writerow([self.pic_url, "new picture", "TDT"])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue())
