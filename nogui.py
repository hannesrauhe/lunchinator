import sys,types
import lunch_server
import lunch_client
import lunch_avatar
import time
import socket
import threading,os
        
class lunchinator_nogui(threading.Thread):
    menu = None
    ls = lunch_server.lunch_server()
    lc = lunch_client.lunch_client()
    
    def __init__(self):           
        threading.Thread.__init__(self)
        self.cmddict = {
               "help": [self.print_help,"prints out this text :-)"],
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
        
if __name__ == "__main__":
    l = lunchinator_nogui()
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
        print "members:"
        for m_ip,m_info in l.ls.get_member_info().iteritems():
            if "name" in m_info:
                print m_info["name"],
            else:
                print m_ip,
        print
    l.stop_server()