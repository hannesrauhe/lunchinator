#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as stripped down CLI-application without self-updating functionality

import __preamble
from lunchinator.lunch_server import *
import time,socket,threading,os,sys,types
        

    
def trace(frame, event, arg):
    print "%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno)
    return trace


if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
#    sys.settrace(trace)
    ls = lunch_server(options.noUpdates)
    ls.start_server()
    
