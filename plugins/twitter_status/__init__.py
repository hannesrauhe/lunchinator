from lunchinator.iface_plugins import iface_called_plugin
from lunchinator import get_server, log_info, log_warning, log_error, log_exception, log_debug

import os,sys,time,pprint

class twitter_status(iface_called_plugin):
    twitter = None
    def __init__(self):
        super(twitter_status, self).__init__()
        self.options = {"twitter_account":""}
        self.other_twitter_users={}
        self.remote_account = ""
        self.remote_member = ""
        
    def activate(self):
        iface_called_plugin.activate(self)
        
    def deactivate(self):
        iface_called_plugin.deactivate(self)
        
    def process_message(self,msg,addr,member_info):
        pass
                
    def process_lunch_call(self,_,__,member_info):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if cmd=="HELO_TWITTER_USER":
            screen_name = value[1:] if value[0]=="@" else value
            if not self.other_twitter_users.has_key(ip) or self.other_twitter_users[ip]!=screen_name:
                self.other_twitter_users[ip]=screen_name        
        
        elif cmd=="HELO_TWITTER_REMOTE":
            screen_name = value[1:] if value[0]=="@" else value
            self.remote_account=screen_name
            self.remote_member=member_info['name'] if member_info and member_info.has_key("name") else ip
            
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout, QComboBox, QSpinBox, QLineEdit, QCheckBox
        from PyQt4.QtCore import Qt
        widget = QWidget(parent)
        w = super(twitter_status, self).create_options_widget(widget)
        layout = QVBoxLayout(widget)
        if len(self.options["twitter_account"]):
            if len(self.remote_account)==0:
                msg = "Nobody in your network has configured a remote account - remote calls not possible"
            else:
                msg = "Mention @%s in a tweet to trigger a remote call from %s"%(self.remote_account,self.remote_member)
        else:
            msg = "Fill in your twitter account to allow remote lunch calls from it"
        
        layout.addWidget(QLabel(msg, widget))
        layout.addWidget(w)
        return widget
            
