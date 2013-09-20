#!/usr/bin/python
#
#this script can be used for sending a message, if the lunchinator is not started or can for some reason not be used
#it sends a message to the members saved in the members-file, 
#no guarantees that you reach everyone in the peer group

import sys
import __preamble
from lunchinator import get_server

if __name__ == "__main__":
    msg = "local"
    if len(sys.argv)>1:
        msg = sys.argv[1]
    
    get_server().with_plugins = False
    recv_nr=get_server().call("HELO_STOP "+msg,client="127.0.0.1")
    print "Sent stop command to local lunchinator"
    
