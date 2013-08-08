from lunchinator.iface_plugins import *
import subprocess, sys, ctypes
from yapsy.PluginManager import PluginManagerSingleton

import urllib2, tempfile, json

class tdtnotify(iface_called_plugin):    
    def __init__(self):
        super(tdtnotify, self).__init__()
        manager = PluginManagerSingleton.get()
        self.ls = manager.app
        self.options = {"icon_file":sys.path[0]+"/images/mini_breakfast.png","blog_name":"tittendestages"}
        
    def activate(self):        
        iface_called_plugin.activate(self)
            
    def process_message(self,msg,addr,member_info):
        if sys.platform.startswith('linux'):    
            try:
                icon = self.options["icon_file"]
                name = " ["+addr+"]"
                if member_info.has_key("name"):
                    name = " [" + member_info["name"] + "]"
                u = urllib2.urlopen("http://api.tumblr.com/v2/blog/"+self.options['blog_name']+".tumblr.com/posts/photo?api_key=SyMOX3RGVS4OnK2bGWBcXNUfX34lnzQJY5FRB6uxpFqjEHz2SY")

                j = json.load(u)
                picurl = j['response']['posts'][0]['photos'][0]['original_size']['url'];

                pic = urllib2.urlopen(picurl)
                localFile = tempfile.NamedTemporaryFile(delete=False)
                icon = localFile.name
                localFile.write(pic.read())
                localFile.flush()
                localFile.close()
                subprocess.call(["notify-send","--icon="+icon, msg + name])
            except:
                self.logger.error("TDT notify error "+str(sys.exc_info()[0]))
        else:
            self.incoming_call_win(msg,addr,member_info)
            
    def process_lunch_call(self,msg,ip,member_info):
        if sys.platform.startswith('linux'):
            self.incoming_call_linux(msg,ip,member_info)
        else:
            self.incoming_call_win(msg,ip,member_info)
        
    def process_event(self,cmd,value,ip,member_info):
        pass