#!/usr/bin/python
import socket,sys,os

def call_peer_nr(msg,peer_nr):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(sys.path[0]+"/lunch_members",'r')    
    i=0
    found=False
    for ip in f.readlines():
        if i==peer_nr:
            #print "sending",msg,"to",ip.strip(),
            try:
                s.sendto(msg, (ip.strip(), 50000)) 
                found=True
                break
            except:              
                pass
                #print "(Exception: hostname unknown)",
        i+=1
    s.close()
    #print ""
    
    if not found:
        i=-1
    return i
    
def call(msg,client=''):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(sys.path[0]+"/lunch_members",'r')
    #print "sending",msg,"to",
    if client:
        #print client
        try:
            s.sendto(msg, (client.strip(), 50000)) 
        except:
            pass
            #print "(Exception: hostname unknown)",
    else:
        for ip in f.readlines():
            #print ip.strip(),
            try:
                s.sendto(msg, (ip.strip(), 50000)) 
            except:
                pass
                #print "(Exception: hostname unknown)",
    
    s.close() 
    #print ""

if __name__ == "__main__":
    msg = "lunch"
    client =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        print client,":",
        client = sys.argv[2]
    print msg
    call(msg,client)
