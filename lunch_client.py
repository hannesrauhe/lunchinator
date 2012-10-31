#!/usr/bin/python
import socket,sys,os

def call(msg,client=''):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(sys.path[0]+"/lunch_members",'r')
    print "sending",msg,"to",
    if client:
        print client
        try:
            s.sendto(msg, (client.strip(), 50000)) 
        except:
            print "(Exception: hostname unknown)",
    else:
        for ip in f.readlines():
            print ip.strip(),
            try:
                s.sendto(msg, (ip.strip(), 50000)) 
            except:
                print "(Exception: hostname unknown)",
    
    s.close()
    print ""

if __name__ == "__main__":
    msg = "lunch"
    client =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        client = sys.argv[2]
    call(msg,client)
