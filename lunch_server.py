#!/usr/bin/python
import socket
import subprocess
from time import gmtime, strftime, localtime
import sys
import os
import ctypes
import lunch_client
import getpass

class lunch_server(object):
    running = False
    auto_update = True
    new_msg = False
    last_messages = [("start","start","start")]
    members = {"127.0.0.1":"myself"}
    
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
        announce_name=True
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
                            
                    elif daten.startswith("HELO"):
                        self.members[addr[0]]=daten.split(" ",1)[1].strip()
                        print self.members
                            
                    else:                            
                        self.incoming_call(daten,addr[0])
                except socket.timeout:
                    if announce_name:                        
                        lunch_client.call("HELO "+getpass.getuser())
                        announce_name=False
                    else:
                        pass
        finally: 
            s.close()                    
            print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service"
    
if __name__ == "__main__":
    l = lunch_server()
    l.start_server()
