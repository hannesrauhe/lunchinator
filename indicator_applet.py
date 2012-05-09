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
                  
    def quit(self,w): 
        self.stop_server(w)
        sys.exit(0)        
    
def send_msg(w,msg):
    lunch_client.call(msg)
    
def msg_window(w):
    # create a new window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)

    # When the window is given the "delete_event" signal (this is given
    # by the window manager, usually by the "close" option, or on the
    # titlebar), we ask it to call the delete_event () function
    # as defined above. The data passed to the callback
    # function is NULL and is ignored in the callback function.
    #window.connect("delete_event", delete_event)

    # Here we connect the "destroy" event to a signal handler.  
    # This event occurs when we call gtk_widget_destroy() on the window,
    # or if we return FALSE in the "delete_event" callback.
    #window.connect("destroy", destroy)

    # Sets the border width of the window.
    window.set_border_width(10)

    # Creates a new button with the label "Hello World".
    button = gtk.Button("Hello World")

    # When the button receives the "clicked" signal, it will call the
    # function hello() passing it None as its argument.  The hello()
    # function is defined above.
    button.connect("clicked", send_msg, "hello world")

    # This will cause the window to be destroyed by calling
    # gtk_widget_destroy(window) when "clicked".  Again, the destroy
    # signal could come from here, or the window manager.
    button.connect_object("clicked", gtk.Widget.destroy, window)

    # This packs the button into the window (a GTK container).
    window.add(button)

    # The final step is to display this newly created widget.
    button.show()

    # and the window
    window.show()
    
    
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
    menu_items.connect("activate", send_msg, "lunch")
    menu_items.show()      
    msg_items = gtk.MenuItem("Send message")
    menu.append(msg_items)      
    msg_items.connect("activate", msg_window)
    msg_items.show()  
    #server_item = gtk.MenuItem("Start Server")
    #menu.append(server_item)      
    #server_item.connect("activate", c.start_server)
    #server_item.show()
    #server_item2 = gtk.MenuItem("Stop Server")
    #menu.append(server_item2)      
    #server_item2.connect("activate", c.stop_server)
    #server_item2.show()
    exit_item = gtk.MenuItem("Exit")
    menu.append(exit_item)      
    exit_item.connect("activate", c.quit)
    exit_item.show()
    
    c.start_server(menu)
    
    ind.set_menu(menu)
    
    gtk.main()
