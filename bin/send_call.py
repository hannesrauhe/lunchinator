#!/usr/bin/python
#
#this script can be used for sending a message, if the lunchinator is not started or can for some reason not be used
#it sends a message to the members saved in the members-file, 
#no guarantees that you reach everyone in the peer group

import sys
import __preamble
from lunchinator import lunch_server

if __name__ == "__main__":
    msg = "lunch"
    cli =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        cli = sys.argv[2]
        print cli,":",
    print msg
    
    c = lunch_server.lunch_server(False,False)
    recv_nr=c.call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    