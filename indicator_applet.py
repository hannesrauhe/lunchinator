#!/usr/bin/python
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
        #auto-update may be working...
        #self.l.auto_update = False
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
            
    def get_last_msgs(self,w):  
        return self.t.l.last_messages
    
    def get_members(self):  
        return self.t.l.members
    
    def check_new_msgs(self):
        return self.t.l.new_msg
    
    def reset_new_msgs(self):
        self.t.l.new_msg=False
                  
    def quit(self,w): 
        self.stop_server(w)
        sys.exit(0)        
    
def send_msg(w,msg=None):
    if msg:
        lunch_client.call(msg)
    else:
        lunch_client.call(w.get_text())
    
def msg_window(w):
    global window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)

    window.set_border_width(10)
    window.set_position(gtk.WIN_POS_CENTER)

    table = gtk.Table(rows=6, columns=3, homogeneous=False)
    window.add(table)
    entry = gtk.Entry()
    table.attach(entry,0,2,5,6)
    entry.show()
    button = gtk.Button("Send Msg")
    table.attach(button,2,3,5,6)    
    button.show()
    m = c.get_last_msgs(None)
    c.reset_new_msgs()
    st = gtk.ListStore(str, str, str)
    for i in m:
        st.append(i)
    treeView = gtk.TreeView(st)
    
    rendererText = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Time", rendererText, text=0)
    column.set_sort_column_id(0)    
    treeView.append_column(column)
    
    rendererText = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Sender", rendererText, text=1)
    column.set_sort_column_id(1)
    treeView.append_column(column)

    rendererText = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Message", rendererText, text=2)
    column.set_sort_column_id(2)
    treeView.append_column(column)
    treeView.show()
    table.attach(treeView,0,1,0,1)
    
    
    
    m = c.get_members()
    st = gtk.ListStore(str, str)
    for i in m.items():
        st.append(i)
    treeView = gtk.TreeView(st)
    
    rendererText = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Member", rendererText, text=0)
    column.set_sort_column_id(0)    
    treeView.append_column(column)
    
    rendererText = gtk.CellRendererText()
    column = gtk.TreeViewColumn("IP", rendererText, text=1)
    column.set_sort_column_id(1)
    treeView.append_column(column)
    treeView.show()
    table.attach(treeView,2,3,0,5)
    
    table.show()
    window.show()
    
    entry.connect("activate", send_msg)
    entry.connect_object("activate", gtk.Widget.destroy, window)
    button.connect_object("clicked", gtk.Widget.activate, entry)
    
def highlight_icon():
    if c.check_new_msgs():
        ind.set_status(appindicator.STATUS_ATTENTION)
    else:
        ind.set_status(appindicator.STATUS_ACTIVE)
    return True
        
    
if __name__ == "__main__": 
    #you need this to use threads and GTK
    gobject.threads_init()
    
    global c
    c = lunch_control()
    
    global ind
    ind = appindicator.Indicator ("lunch notifier",
                                "news-feed",
                                appindicator.CATEGORY_COMMUNICATIONS)
    ind.set_status (appindicator.STATUS_ACTIVE)
    ind.set_attention_icon ("gksu-root-terminal")
    
    # create a menu
    menu = gtk.Menu()    
    menu_items = gtk.MenuItem("Call for lunch")
    menu.append(menu_items)      
    menu_items.connect("activate", send_msg, "lunch")
    menu_items.show()      
    msg_items = gtk.MenuItem("Show/Send messages")
    menu.append(msg_items)      
    msg_items.connect("activate", msg_window)
    msg_items.show()  
    exit_item = gtk.MenuItem("Exit")
    menu.append(exit_item)      
    exit_item.connect("activate", c.quit)
    exit_item.show() 
    #test_item = gtk.MenuItem("Test")
    #menu.append(test_item)      
    #test_item.connect("activate", highlight_icon)
    #test_item.show()
    
    c.start_server(menu)
    
    ind.set_menu(menu)
    
    gobject.timeout_add(2000, highlight_icon)
    gtk.main()
