from lunchinator.iface_plugins import iface_called_plugin
import subprocess, sys, ctypes, threading, time, urllib2, json
from cStringIO import StringIO, OutputType
from lunchinator import get_server, log_exception, log_warning, \
    get_settings, convert_string, log_error, log_debug, log_info

import urllib2, tempfile, json, time, contextlib, csv

class tdtThread(threading.Thread):
    def __init__(self, url, interval):
        super(tdtThread, self).__init__()
        self.running = False
        self.failed_attempts = 0
        self.url = url
        self.interval = interval
        self.next_time = time.time()
        self.pic_url = ""
        self.http_result = None
        
    def run(self):
        log_info("Starting TDT Download Thread")
        self.running = True
        while(self.running):
            if time.time()>=self.next_time:
                if self.download():
                    self.failed_attempts = 0
                    self.parse_json()
                    self.next_time = time.time()+self.interval
                else: #something went wrong: try again in 5 seconds
                    self.failed_attempts += 1
                    if self.failed_attempts>=5:
                        log_error("TDT too many failed attempts, I stop trying")
                        self.running = False
                    self.next_time = time.time()+5
            time.sleep(5)
            
    def download(self):            
        try:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(self.url, headers=hdr)
            with contextlib.closing(urllib2.urlopen(req)) as u:
                self.http_result = u.read()
            return True
        except urllib2.HTTPError as e:
            log_error("TDT: Error while downloading %s (%s)" % (self.url, e))
            return False
        except:
            log_exception("TDT: Error while downloading %s" % self.url)
            return False
        
    def parse_json(self):
        if not self.http_result:
            return False
        
        j = json.loads(self.http_result)
        
        oldurl = self.pic_url
        self.pic_url = j['response']['posts'][0]['photos'][0]['original_size']['url']
        if oldurl!=self.pic_url:
            log_info("TDT: New picture! Yeay!")
            get_server().call("HELO_TDTNOTIFY_NEW_PIC "+self.pic_url)
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter = ' ', quotechar = '"')
                writer.writerow([self.pic_url, "new picture from %s"%time.strftime("%b %d %Y %H:%M"), "TDT"])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue())

class tdtnotify(iface_called_plugin):
    def __init__(self):
        super(tdtnotify, self).__init__()
        self.options = {"blog_name":"tittendestages",
                        "polling_time":30}
        
        self.thread = None
        
    def activate(self):        
        iface_called_plugin.activate(self)
            
        self.thread = tdtThread("http://api.tumblr.com/v2/blog/"+self.options['blog_name']+\
                                ".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY",\
                                60*self.options["polling_time"])
        self.thread.start()
    
    def deactivate(self): 
        if self.thread:       
            self.thread.running = False
            log_info("Waiting for TDT Thread to stop")
            self.thread.join()
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,_,__):
        if cmd=="HELO_TDTNOTIFY_NEW_PIC" and self.thread:
            #somebody found a new pic -> search immediately
            self.thread.next_time = time.time()
        
