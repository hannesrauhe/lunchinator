import sys,types
from lunchinator.lunch_server import *
import time
import socket
import threading,os
from lunch_options import optionParser
        
class lunchinator_nogui(threading.Thread):
    menu = None
    ls = None
    
    def __init__(self, noUpdates = False):
        threading.Thread.__init__(self)
        self.ls = lunch_server(noUpdates)
        self.cmddict = {
               "help": [self.print_help,"prints out this text :-)"],
                "members": [self.print_members,"prints the list of members"],
               "call": [self.ls.call_all_members,"calls for lunch"],
               "q": [self.stop_server, "exit"]}
    
    def run(self):
        self.ls.start_server()   

    def stop_server(self):        
        if self.isAlive():
            self.ls.running = False
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
        for m_ip,m_info in self.ls.get_member_info().iteritems():
            if "name" in m_info:
                print m_info["name"],
            else:
                print m_ip,
        
if __name__ == "__main__":
    (options, args) = optionParser.parse_args()
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