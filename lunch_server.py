#!/usr/bin/python
import socket
import subprocess
from time import gmtime, strftime, localtime, time
import sys
import os
import ctypes
import lunch_client
import getpass
import json

class lunch_server(object):
    audio_file ="sonar.wav"
    user_name = ""
    running = False
    auto_update = True
    update_request = False
    new_msg = False
    my_master = -1
    last_messages = [("start","start","start")]
    members = {"127.0.0.1":"myself"}
    member_timeout = {"127.0.0.1":time()}
    
    '''will be called every ten seconds'''
    def read_config(self):    
        if os.path.exists(sys.path[0]+"/username.cfg"):
            with open(sys.path[0]+"/username.cfg") as f:
                self.user_name = f.readline().strip()
        else:
             self.user_name = getpass.getuser()
        if os.path.exists(sys.path[0]+"/sound.cfg"):
            with open(sys.path[0]+"/sound.cfg") as f:
                audio_file = f.readline().strip()
                if os.path.exists(sys.path[0]+"/sounds/"+audio_file):
                    self.audio_file = audio_file
                else:
                    print "configured audio file "+audio_file+" does not exist in sounds folder, using old one: "+self.audio_file
        
    def get_user_name(self):
        return self.user_name
    
    def incoming_call(self,msg,addr):
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        m = addr
        if addr in self.members:
            m = self.members[addr]
        print "%s: [%s] %s" % (t,m, msg)
        
        self.last_messages.append((t,m,msg))
        if len(self.last_messages)>5:
            self.last_messages.pop(0)
        self.new_msg = True
            
        if sys.platform.startswith('linux'):
            self.incoming_call_linux(msg,m)
        else:
            self.incoming_call_win(msg,m)
            
    def incoming_call_linux(self,msg,addr):    
        try:
            subprocess.call(["notify-send", msg + " [" + addr + "]"])
        except:
            print "notify error"
            pass
    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (open)"
                pass
        
            try:
                subprocess.call(["play", "-q", sys.path[0]+"/sounds/"+self.audio_file])    
            except:
                print "sound error"
                pass
        
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (close)"
                pass
        
    def incoming_call_win(self,msg,addr):    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                print "eject error (open)"
                pass
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                print "eject error (close)"
                pass
    
    def start_server(self):
        print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service"
        self.running = True        
        self.members = lunch_client.build_members_from_file()
        self.my_master=-1 #the peer i use as master
        self.user_name=getpass.getuser()
        peer_nr=0 #the number of the peer i contacted to be my master
        announce_name=0 #how often did I announce my name
        
        self.read_config()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            while self.running:
                try:
                    daten, addr = s.recvfrom(1024) 
#three types of messages: 1. call for application update'''
                    if daten.startswith("update"):
                        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                        if self.auto_update:
                            print "%s: [%s] update and restart" % (t,addr)
                            os.chdir(sys.path[0])
                            subprocess.call(["git","pull"])
                            s.close()
                            os.execlp("python","python",os.path.basename(sys.argv[0]))
                        else:
                            print "%s: %s issued an update but updates are disabled" % (t,addr)
                            self.update_request = True
#2. simple infrastructure protocoll messages starting with HELO'''                            
                    elif daten.startswith("HELO"):
                        if not addr[0].startswith("127."):
                            try:
                                self.member_timeout[addr[0]]=time()
                                if daten.startswith("HELO_DICT"):
                                    #the master send me the list of members - yeah
                                    ext_members = json.loads(daten.split(" ",1)[1].strip())
                                    self.members.update(ext_members)
                                    self.members = dict((k, v) for k, v in self.members.items() if not k.startswith("127"))
                                    #self.members["127.0.0.1"] = "myself"
                                    self.my_master = addr[0]
                                    print "got new members from",self.my_master,":",json.dumps([item for item in ext_members.keys() if not self.members.has_key(item)])
                                    
                                elif daten.startswith("HELO_MASTER"):
                                    #someone thinks i'm the master - I'll send him the members I know
                                    print "I'm the master for",addr[0]
                                    members_from_file=lunch_client.build_members_from_file()
                                    members_from_file.update(self.members)
                                    self.members = members_from_file
                                    self.members[addr[0]]=daten.split(" ",1)[1].strip()
                                    lunch_client.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
                                else:
                                    #someone tells me his name
                                    self.members[addr[0]]=daten.split(" ",1)[1].strip()
                            except:
                                print "Unexpected error while handling HELO call: ", sys.exc_info()[0]
                                print "The data send was:",daten
#3. everything else is a message that should be displayed to the user'''                            
                    else:                            
                        self.incoming_call(daten,addr[0])
                except socket.timeout:
                    self.read_config()
                    if self.my_master==-1:        
                        #I'm still waiting for someone to send me his list of members
                        peer_nr = lunch_client.call("HELO_MASTER "+self.get_user_name(),peer_nr=peer_nr)
                    if announce_name==10:
                        #it's time to announce my name again
                        lunch_client.call("HELO "+self.get_user_name(),hosts=self.members)
                        announce_name=0
                    else:
                        #just wait for the next time when i have to announce my name
                        announce_name+=1
        finally: 
            s.close()                    
            print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service"
    
if __name__ == "__main__":
    l = lunch_server()
    l.start_server()
