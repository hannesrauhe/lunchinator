#!/usr/bin/python
import socket
import subprocess
from time import gmtime, strftime, localtime
import sys
import os
import ctypes

class lunch_server(object):
    running = False
    def incoming_call(self,msg,addr):
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        print "%s: [%s] %s" % (t,addr, msg)
    
        try:
            subprocess.call(["notify-send", msg + " [" + addr + "]"])
        except:
            pass
    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                pass
        
            try:
                subprocess.call(["play", "-q", sys.path[0]+"/sounds/sonar.wav"])    
            except:
                pass
        
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                pass
            
    def incoming_call_win(self,msg,addr):
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        print "%s: [%s] %s" % (t,addr, msg)
    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                pass
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door close", None, 0, None)
            except:
                pass
    
    def start_server(self):
        self.running = True
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service"
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            while self.running:
                try:
                    daten, addr = s.recvfrom(1024) 
                    if daten.startswith("update"):
                        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                        print "%s: [%s] update and restart" % (t,addr)
                        os.chdir(sys.path[0])
                        subprocess.call(["git","pull"])
                        s.close()
                        os.execlp("python","python","lunch_server.py")
                    else:
                        if sys.platform.startswith('linux'):
                            self.incoming_call(daten,addr[0])
                        else:
                            self.incoming_call_win(daten,addr[0])
                except socket.timeout:
                    pass
        finally: 
            s.close()
                    
        print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service"
    
if __name__ == "__main__":
    l = lunch_server()
    l.start_server()
