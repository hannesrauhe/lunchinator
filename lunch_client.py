#!/usr/bin/python
import socket,sys,os

def call(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(sys.path[0]+"/lunch_members",'r')
    print "sending",msg,"to",
    for ip in f.readlines():
        print ip.strip(),
        # this command sends some data over the network on port 50000
        try:
            s.sendto(msg, (ip.strip(), 50000)) 
        except:
            print "(Exception: hostname unknown)",
    
    s.close()
    print ""

if __name__ == "__main__":
    msg = "lunch"
    if len(sys.argv)>1:
        msg = sys.argv[1]
    call(msg)
