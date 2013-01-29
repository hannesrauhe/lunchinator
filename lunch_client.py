#!/usr/bin/python
import socket,sys,os

def build_members_from_file():
    members = {}
    f = open(sys.path[0]+"/lunch_members.cfg",'r')    
    for hostn in f.readlines():
        try:
            members[socket.gethostbyname(hostn.strip())]=hostn.strip()
        except:
            pass
    if len(members)<=1:
        print "Warning: Less than two host of the members file are online - names could not be resolved"
    return members
        
def call(msg,client='',hosts={}):
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
        members = build_members_from_file()
        for ip,name in members.items():
            try:
                s.sendto(msg, (ip.strip(), 50000))
                i+=1
            except:
                #print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
                continue
    else:
        for ip,name in hosts.items():
            #print ip.strip()
            try:
                s.sendto(msg, (ip.strip(), 50000))
                i+=1
            except:
                #print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
                continue
    
    s.close() 

if __name__ == "__main__":
    msg = "lunch"
    cli =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        cli = sys.argv[2]
        print cli,":",
    print msg
    
    recv_nr=call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
