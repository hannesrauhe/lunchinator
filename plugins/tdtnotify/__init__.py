from lunchinator.iface_plugins import *
import subprocess, sys, ctypes
from yapsy.PluginManager import PluginManagerSingleton

import urllib2, tempfile, json, time

class tdtnotify(iface_called_plugin):    
    def __init__(self):
        super(tdtnotify, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        self.options = {"icon_file":sys.path[0]+"/images/mini_breakfast.png",
                        "blog_name":"tittendestages",
                        "trigger_word":"",
                        "polling_time":30}
        self.last_time=0
        self.rotate_counter=0
        self.pic_url = ""
        self.localFile = None
        
    def activate(self):        
        iface_called_plugin.activate(self)
        self.last_time=0
        self.rotate_counter=0
        self.pic_url = ""
        self.localFile = tempfile.NamedTemporaryFile()
        self.download_pic(True)
        self.shared_dict["tdtnotify_file"] = self.localFile.name
    
    def deactivate(self):        
        self.localFile.close()
        del self.shared_dict["tdtnotify_file"]
        iface_called_plugin.deactivate(self)
            
    def process_message(self,msg,addr,member_info):
        pass
                
    def download_pic(self,force=False):
        try:
            u = urllib2.urlopen("http://api.tumblr.com/v2/blog/"+self.options['blog_name']+".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY")

            j = json.load(u)
            #if :
            #    self.rotate_counter = 0
            oldurl = self.pic_url
            self.pic_url = j['response']['posts'][self.rotate_counter]['photos'][0]['original_size']['url'];
            if force or oldurl!=self.pic_url:
                pic = urllib2.urlopen(self.pic_url)
                self.localFile.seek(0)
                self.localFile.truncate()
                self.localFile.write(pic.read())
                self.localFile.flush()
                return True
            else:
                return False
        except:
            self.logger.error("TDT notify error while downloading: "+str(sys.exc_info()[0]))
            
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        if cmd=="HELO_TDTNOTIFY_NEW_PIC" or (time.time()-self.last_time) > (60*self.options["polling_time"]):
            if not cmd=="HELO_TDTNOTIFY_NEW_PIC":
                self.ls.call("HELO_TDTNOTIFY_POLL "+str(self.options["polling_time"]))
                
            if self.download_pic(value=="force"):
                self.ls.call("HELO_TDTNOTIFY_NEW_PIC "+self.pic_url)
                self.notify()       
            self.last_time = time.time() 
                
    def notify(self):
        if sys.platform.startswith('linux'):   
            try:
                icon = self.options["icon_file"]
                icon = self.localFile.name
                subprocess.call(["notify-send","--icon="+icon, "TDT", "new pic"])
                #self.rotate_counter+=1
            except:
                self.logger.error("TDT notify error "+str(sys.exc_info()[0]))
                