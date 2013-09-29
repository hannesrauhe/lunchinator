#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as stripped down CLI-application without self-updating functionality

import __preamble
from lunchinator import get_server, lunch_settings
import time,socket,os,sys,types
        

    
def trace(frame, event, arg):
    print "%s, %s:%d" % (event, frame.f_code.co_filename, frame.f_lineno)
    return trace


if __name__ == "__main__":
    (options, args) = lunch_settings.lunch_options_parser().parse_args()
#    sys.settrace(trace)
    get_server().no_updates = options.noUpdates
    get_server().start_server()
    
