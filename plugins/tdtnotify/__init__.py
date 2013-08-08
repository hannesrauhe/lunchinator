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
                        "rotation_time_reset":4}
        self.last_time=0
        self.rotate_counter=0
        
    def activate(self):        
        iface_called_plugin.activate(self)
        self.localFile = tempfile.NamedTemporaryFile()
        self.download_pic()
        self.shared_dict["tdtnotify_file"] = self.localFile.name
    
    def deactivate(self):        
        self.localFile.close()
        iface_called_plugin.deactivate(self)
            
    def process_message(self,msg,addr,member_info):
        if sys.platform.startswith('linux') and (len(self.options['trigger_word'])==0 or msg.find(self.options['trigger_word'])!=-1):    
            try:
                icon = self.options["icon_file"]
                name = " ["+addr+"]"
                if member_info.has_key("name"):
                    name = " [" + member_info["name"] + "]"
                self.download_pic                
                icon = self.localFile.name
                subprocess.call(["notify-send","--icon="+icon, name, msg])
                self.last_time = time.time()
                self.rotate_counter+=1
            except:
                self.logger.error("TDT notify error "+str(sys.exc_info()[0]))
                
    def download_pic(self):
        try:
            u = urllib2.urlopen("http://api.tumblr.com/v2/blog/"+self.options['blog_name']+".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY")

            j = json.load(u)
            if (time.time()-self.last_time) > (3600*self.options["rotation_time_reset"]):
                self.rotate_counter = 0
            picurl = j['response']['posts'][self.rotate_counter]['photos'][0]['original_size']['url'];

            pic = urllib2.urlopen(picurl)
            self.localFile.seek(0)
            self.localFile.truncate()
            self.localFile.write(pic.read())
            self.localFile.flush()
        except:
            self.logger.error("TDT notify error while downloading: "+str(sys.exc_info()[0]))
            
    def process_lunch_call(self,msg,ip,member_info):
        if sys.platform.startswith('linux'):
            self.incoming_call_linux(msg,ip,member_info)
        else:
            self.incoming_call_win(msg,ip,member_info)
        
    def process_event(self,cmd,value,ip,member_info):
        pass