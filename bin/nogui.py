#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as stripped down CLI-application without self-updating functionality

import __preamble
from lunchinator import get_server
from lunchinator.lunch_settings import lunch_options_parser
import time,socket,threading,os,sys,types
        
class lunchinator_nogui(threading.Thread):
    menu = None
    
    def __init__(self, noUpdates = False):
        threading.Thread.__init__(self)
        get_server().no_updates = noUpdates
        self.cmddict = {
               "help": [self.print_help,"prints out this text :-)"],
                "members": [self.print_members,"prints the list of members"],
               "call": [get_server().call_all_members,"calls for lunch"],
               "q": [self.stop_server, "exit"]}
    
    def run(self):
        get_server().start_server()   

    def stop_server(self):        
        if self.isAlive():
            get_server().running = False
            self.join()  
            print "server stopped" 
        else:
            print "server not running"
    
    def print_help(self):
        for k,v in self.cmddict.iteritems():
            print k,"-",v[1]        
        
    def process_cmd(self,cmdstring):
        if cmdstring=="":
            return
        args = cmdstring.split()
        cmd = args[0]
        args.pop(0)
        if cmd in self.cmddict:
            if len(args):
                self.cmddict[cmd][0](*args)
            else:    
                self.cmddict[cmd][0]()
        else:
            print "command not known"
            
    def print_members(self):
        print "members:",
        for m_ip,m_info in get_server().get_member_info().iteritems():
            if "name" in m_info:
                print m_info["name"],
            else:
                print m_ip,

if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
    l = lunchinator_nogui(options.noUpdates)
    l.start()
    time.sleep(1)
    cmd = ""
    while l.isAlive() and cmd not in ["exit","q","quit"]:
        cmd = raw_input(">")
        try:
            l.process_cmd(cmd)            
        except:
            print "Unexpected error:", sys.exc_info()[0]
            print sys.exc_info()[1]
        print
    l.stop_server()