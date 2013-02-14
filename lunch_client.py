#!/usr/bin/python
from lunch_default_config import *
import socket,sys,os

class lunch_client(lunch_default_config):
    def build_members_from_file(self):
        members = {}
        try:
            f = open(self.members_file,'r')    
            for hostn in f.readlines():
                try:
                    members[socket.gethostbyname(hostn.strip())]=hostn.strip()
                except:
                    pass
            if len(members)<=1:
                print "Warning: Less than two host of the members file are online - names could not be resolved"
        except:
            print "lunch_members.cfg does not exist - are you connected to anyone?"
        return members
            
    def call(self,msg,client='',hosts={}):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        i=0
        #print "sending",msg,"to",
        if client:
            #print client
            try:
                s.sendto(msg, (client.strip(), 50000)) 
                i+=1
            except:
                print "Exception while sending msg %s to %s:"%(msg,client), sys.exc_info()[0]
        elif 0==len(hosts):
            members = self.build_members_from_file()
            for ip,name in members.items():
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    #print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
                    continue        
            s.sendto(msg, ("127.0.0.1", 50000))
        else:
            for ip,name in hosts.items():
                #print ip.strip()
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    #print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
                    continue
            s.sendto(msg, ("127.0.0.1", 50000))
        
        s.close() 
        return i

if __name__ == "__main__":
    msg = "lunch"
    cli =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        cli = sys.argv[2]
        print cli,":",
    print msg
    
    c = lunch_client()
    recv_nr=c.call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
