#!/usr/bin/python
import socket
import subprocess
from time import gmtime, strftime, localtime
import sys
import os
import ctypes
import lunch_client
import getpass
import json

class lunch_server(object):
    user_name = ""
    running = False
    auto_update = True
    update_request = False
    new_msg = False
    my_master = -1
    last_messages = [("start","start","start")]
    members = {"127.0.0.1":"myself"}
    
    def get_user_name(self):
        if self.user_name:
            return user_name
        else:
            return getpass.getuser()
    
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
                subprocess.call(["play", "-q", sys.path[0]+"/sounds/sonar.wav"])    
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
        got_members=False #i do not have any master yet... 
        self.my_master=-1 #the peer i use as master
        peer_nr=-1 #the number of the peer i contacted to be my master
        announce_name=0 #how often did I announce my name
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            while self.running:
                try:
                    daten, addr = s.recvfrom(1024) 
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
                            
                    elif daten.startswith("HELO"):
                        try:
                            if daten.startswith("HELO_DICT"):
                                #the master send me the list of members - yeah
                                ext_members = daten.split(" ",1)[1].strip()
                                self.members.update(json.loads(ext_members))
                                self.members["127.0.0.1"] = "myself"
                                if len(self.members)>2:
                                    got_members=True
                                    self.my_master = addr[0]
                                    print "got members from",self.my_master,":",json.dumps(self.members)
                                else:
                                    print "got members from",addr[0],"but not enough -- continue trying"
                                
                            elif daten.startswith("HELO_MASTER"):
                                #someone thinks i'm the master - I'll send him the members I know
                                print "I'm the master for",addr[0]
                                self.members[addr[0]]=daten.split(" ",1)[1].strip()
                                lunch_client.call("HELO_DICT "+json.dumps(self.members),addr[0])
                            else:
                                #someone tells me his name    
                                if addr[0]!="127.0.0.1":
                                    self.members[addr[0]]=daten.split(" ",1)[1].strip()
                        except:
                            print "Unexpected error while handling HELO call: ", sys.exc_info()[0]
                            print "The data send was:",daten
                            
                    else:                            
                        self.incoming_call(daten,addr[0])
                except socket.timeout:
                    if not got_members:        
                        #I'm still waiting for someone to send me his list of members   
                        peer_nr+=1                     
                        peer_nr = lunch_client.call_peer_nr("HELO_MASTER "+getpass.getuser(),peer_nr)
                    elif announce_name==10:
                        #it's time to announce my name again
                        lunch_client.call("HELO "+self.get_user_name())
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
