#!/usr/bin/python
import socket,sys,os

def build_members_from_file():
    members = {}
    f = open(sys.path[0]+"/lunch_members",'r')    
    for hostn in f.readlines():
        try:
            members[socket.gethostbyname(hostn.strip())]=hostn.strip()
        except:
            pass
    if len(members)<=1:
        print "Warning: Less than two host of the members file are online"
    return members
        
def call(msg,client='',hosts={},peer_nr=-1):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    found_peer=False;
    i=0
    #print "sending",msg,"to",
    if client:
        #print client
        try:
            s.sendto(msg, (client.strip(), 50000)) 
            i+=1
        except:
            print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
    else:
        members = build_members_from_file()
        members.update(hosts)
        for ip,name in members.items():
            #print i,
            if ip.startswith("127."):
                continue
            if i==peer_nr or peer_nr==-1:
                #print ip.strip()
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    if peer_nr!=-1:
                        found_peer=True
                        i+=1
                        break 
                except:
                    #print "Exception while sending msg %s to %s:"%(ip,name), sys.exc_info()[0]
                    continue
            i+=1
    
    s.close() 
    #print ""
    if peer_nr!=-1 and not found_peer:
        i=0
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
    
    recv_nr=call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
