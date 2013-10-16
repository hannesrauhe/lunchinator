#!/usr/bin/python
#
#this script can be used for sending a message, if the lunchinator is not started or can for some reason not be used
#it sends a message to the members saved in the members-file, 
#no guarantees that you reach everyone in the peer group

import sys,os
path = os.path.abspath(sys.argv[0])
while os.path.dirname(path) != path:
    if os.path.exists(os.path.join(path, 'lunchinator', '__init__.py')):
        sys.path.insert(0, path)
        break
    path = os.path.dirname(path)
    
from lunchinator import get_server

if __name__ == "__main__":
    msg = "lunch"
    cli =''
    if len(sys.argv)>1:
        msg = sys.argv[1]
    if len(sys.argv)>2:
        cli = sys.argv[2]
        print cli,":",
    print msg
    
    get_server().set_plugins_enabled(False)
    recv_nr=get_server().call(msg,client=cli)
    print "sent to",recv_nr,"clients"
    
