from lunchinator import get_server, get_settings, convert_string, get_peers
from lunchinator.log import getLogger
from lunchinator.logging_mutex import loggingMutex
from lunchinator.plugin import iface_called_plugin

import subprocess, sys, ctypes, threading, time, urllib2, json
from cStringIO import StringIO, OutputType
from functools import partial
import tempfile, contextlib, csv
from threading import Timer, Lock

class tdtnotify(iface_called_plugin):
    def __init__(self):
        super(tdtnotify, self).__init__()
        self.options = {"blog_name":"tittendestages",
                        "polling_time":30}
        
        self.url = "http://api.tumblr.com/v2/blog/" + self.options['blog_name'] + \
                    ".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY"
        
        self.timer = None
        self.lock = loggingMutex("TDTNotify", logging=get_settings().get_verbose())
        
    def activate(self):        
        iface_called_plugin.activate(self)
        
        self.failed_attempts = 0
        self.pic_url = ""
        
        self._startCheckTimer(immediately=True)
    
    def deactivate(self): 
        # if we are checking right now, finish checking first
        with self.lock:
            if self.timer != None:
                self.timer.cancel()       
        iface_called_plugin.deactivate(self)
        
    def process_message(self, msg, addr, member_info):
        pass
            
    def process_lunch_call(self, msg, ip, member_info):
        pass
        
    def process_event(self, cmd, _value, ip, _peerInfo, _prep):
        if cmd == "HELO_TDTNOTIFY_NEW_PIC":
            if not get_peers().isMe(pIP=ip):
                # somebody found a new pic -> search immediately
                Timer(0, partial(self.check, restart=False)).start()
        
    def _startCheckTimer(self, immediately=False):
        if immediately:
            timeout = 30
        elif self.failed_attempts == 0:
            timeout = 60 * self.options["polling_time"]
        elif self.failed_attempts < 5:
            # something went wrong: try again in 5 seconds
            timeout = 5
        else:
            # too many failed attempts
            getLogger().error("TDTNotify: too many failed attempts, I stop trying")
            return
            
        self.timer = Timer(timeout, self.check)
        self.timer.start()
        
    ############# On background thread ###############
    
    def check(self, restart=True):
        with self.lock:
            success, http_result = self.download()
            if success:
                self.failed_attempts = 0
                self.parse_json(http_result)
            else:
                self.failed_attempts += 1
            if restart:
                self._startCheckTimer()

    def download(self):            
        try:
            hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            req = urllib2.Request(self.url, headers=hdr)
            with contextlib.closing(urllib2.urlopen(req)) as u:
                http_result = u.read()
            return True, http_result
        except urllib2.HTTPError as e:
            getLogger().error("TDT: Error while downloading %s (%s)", self.url, e)
            return False, None
        except:
            getLogger().exception("TDT: Error while downloading %s", self.url)
            return False, None
        
    def parse_json(self, http_result):
        if not http_result:
            return False
        
        j = json.loads(http_result)
        
        oldurl = self.pic_url
        self.pic_url = j['response']['posts'][0]['photos'][0]['original_size']['url']
        if oldurl != self.pic_url:
            getLogger().info("TDT: New picture! Yeay!")
            get_server().call("HELO_TDTNOTIFY_NEW_PIC " + self.pic_url)
            with contextlib.closing(StringIO()) as strOut:
                writer = csv.writer(strOut, delimiter=' ', quotechar='"')
                writer.writerow([self.pic_url, "new picture from %s" % time.strftime("%b %d %Y %H:%M"), "TDT"])
                get_server().call('HELO_REMOTE_PIC %s' % strOut.getvalue())
