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
    
    def run(self):
        self.ls.start_server()   

    def stop_server(self):        
        if self.isAlive():
            self.ls.running = False
            self.join()  
            print "server stopped" 
        else:
            print "server not running"
        
if __name__ == "__main__":
    l = lunchinator_nogui()
    l.start()
    time.sleep(1)
    cmd = ""
    while l.isAlive() and cmd not in ["exit","q","quit"]:
        cmd = raw_input(">")
        print l.ls.get_member_info()
    l.stop_server()