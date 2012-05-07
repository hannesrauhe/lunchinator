#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.
#
# Authors: Neil Jagdish Patel <neil.patel@canonical.com>
#          Jono Bacon <jono@ubuntu.com>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#
import sys
import gobject
import gtk
import appindicator
import lunch_server
import lunch_client
import threading

class ServerThread(threading.Thread): 
    l = lunch_server.lunch_server()
    def __init__(self): 
        self.l.auto_update = False
        threading.Thread.__init__(self) 
 
    def run(self):
        self.l.start_server()
        
    def stop_server(self):
        self.l.running = False

class lunch_control():
    t = ServerThread()
        
    def start_server(self,w):
        if not self.t.isAlive():
            self.t = ServerThread()
            self.t.start()
        else:
            print "server already running"
            
    def stop_server(self,w):        
        if self.t.isAlive():
            self.t.stop_server()
            self.t.join()  
            print "server stopped" 
        else:
            print "server not running"  
                  
    def quit(self,w): 
        self.stop_server(w)
        sys.exit(0)
        
def menuitem_response(w, buf):
    lunch_client.call("lunch")
    
    
if __name__ == "__main__": 
    #you need this to use threads and GTK
    gobject.threads_init()
    
    c = lunch_control()
    
    ind = appindicator.Indicator ("lunch notifier",
                                "news-feed",
                                appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_status (appindicator.STATUS_ACTIVE)
    ind.set_attention_icon ("indicator-messages-new")
    
    # create a menu
    menu = gtk.Menu()    
    menu_items = gtk.MenuItem("Call for lunch")
    menu.append(menu_items)      
    menu_items.connect("activate", menuitem_response, "")
    menu_items.show()  
    server_item = gtk.MenuItem("Start Server")
    menu.append(server_item)      
    server_item.connect("activate", c.start_server)
    server_item.show()
    server_item = gtk.MenuItem("Stop Server")
    menu.append(server_item)      
    server_item.connect("activate", c.stop_server)
    server_item.show()
    exit_item = gtk.MenuItem("Exit")
    menu.append(exit_item)      
    exit_item.connect("activate", c.quit)
    exit_item.show()
    
    c.start_server(menu)
    
    ind.set_menu(menu)
    
    gtk.main()
