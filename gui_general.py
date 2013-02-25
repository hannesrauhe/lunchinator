import sys
import gobject
import gtk
import lunch_server
import lunch_client
import lunch_avatar
import lunch_http
import time
import socket
import threading

import urllib2
                 
        
class lunchinator(threading.Thread):
    menu = None
    ls = lunch_server.lunch_server()
    lanschi_http = None
    
    def __init__(self):           
        threading.Thread.__init__(self)    
        self.init_menu()      
        if self.ls.get_http_server():            
            self.lanschi_http = lunch_http.lunch_http(self.ls)
            self.lanschi_http.start()
    
    def run(self):
        self.ls.start_server()      
    
    def init_menu(self):
        #create the settings submenu
        settings_menu = gtk.Menu()
        avatar_item = gtk.CheckMenuItem("Avatar")
        debug_item = gtk.CheckMenuItem("Debug Output")
        http_server_item = gtk.CheckMenuItem("Run HTTP Server")
        settings_item = gtk.CheckMenuItem("More Settings")
        
        debug_item.set_active(self.ls.get_debug())
        http_server_item.set_active(self.ls.get_http_server())
        avatar_item.set_active(len(self.ls.get_avatar())>0)
            
        debug_item.connect("activate", self.toggle_debug_mode)
        http_server_item.connect("activate",self.toggle_http_server)
        avatar_item.connect("activate", self.select_avatar)
                
        settings_menu.append(avatar_item)
        settings_menu.append(debug_item)
        settings_menu.append(http_server_item)
        settings_menu.append(settings_item)
        settings_menu.show_all()
        
        #main menu
        self.menu = gtk.Menu()    
        menu_items = gtk.MenuItem("Call for lunch")
        msg_items = gtk.MenuItem("Show/Send messages")
        settings_item = gtk.MenuItem("Settings")
        exit_item = gtk.MenuItem("Exit")
                
        menu_items.connect("activate", send_msg, self, "lunch")
        msg_items.connect("activate", msg_window, self)
        settings_item.set_submenu(settings_menu)
        exit_item.connect("activate", self.quit)
        
        menu_items.show()         
        msg_items.show()
        settings_item.show() 
        exit_item.show()
        
        self.menu.append(menu_items)
        self.menu.append(msg_items)  
        self.menu.append(settings_item)
        self.menu.append(exit_item) 
        
    def toggle_debug_mode(self,w):
        self.ls.set_debug(w.get_active())
        
    def toggle_http_server(self,w):   
        self.ls.set_http_server(w.get_active()) 
        if w.get_active():
            #give the actual lunch_server thread with its configuration-variables to the http_server
            self.lanschi_http = lunch_http.lunch_http(self.ls)
            self.lanschi_http.start()
        else:
            self.lanschi_http.stop_server()
        
    def select_avatar(self,w):
        chooser = gtk.FileChooserDialog(title="Choose your avatar",action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        fi = gtk.FileFilter()
        fi.set_name("Images")
        fi.add_mime_type("image/png")
        fi.add_mime_type("image/jpeg")
        fi.add_mime_type("image/gif")
        fi.add_pattern("*.png")
        fi.add_pattern("*.jpg")
        fi.add_pattern("*.gif")
        fi.add_pattern("*.tif")
        fi.add_pattern("*.xpm")
        chooser.add_filter(fi)
        chooser.run()
        response = chooser.run()
        if response == gtk.RESPONSE_OK:   
            filename = chooser.get_filename()
            l_av = lunch_avatar.lunch_avatar()
            l_av.use_as_avatar(filename)
        chooser.destroy()       
        
    def stop_server(self,w):        
        if self.isAlive():
            self.ls.running = False
            self.join()  
            print "server stopped" 
        else:
            print "server not running"
            
    def get_last_msgs(self,w):  
        return self.ls.last_messages
    
    def get_members(self):  
        return self.ls.members

    def get_member_timeout(self):  
        return self.ls.member_timeout
    
    def check_new_msgs(self):
        return self.ls.new_msg
    
    def reset_new_msgs(self):
        self.ls.new_msg=False
        
    def disable_auto_update(self):
        self.ls.auto_update=False

    def set_user_name(self,name):
        self.ls.user_name=name
                  
    def quit(self,w): 
        self.stop_server(w)
        if self.ls.get_http_server():
            self.lanschi_http.stop_server()
        sys.exit(0)  
        
        
    
def send_msg(w,*data):
    lc = lunch_client.lunch_client()
    c = data[0]
    if len(data)>1:
        lc.call(data[1],hosts=c.get_members())
    else:
        lc.call(w.get_text())
        
def add_host(w,*data):
    hostn = w.get_text()
    c = data[0]
    try:
        c.t.ls.members[socket.gethostbyname(hostn.strip())]=hostn.strip()
    except:
        d = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=None)
        d.set_markup("Cannot add host: Hostname unknown")
        d.run()

class UpdatingTable(object):    
    def __init__(self,box,c):
        self.c = c        
        self.treeView = gtk.TreeView(self.create_model())
        self.fill_treeview()
        self.scrollTree = gtk.ScrolledWindow()
        self.scrollTree.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollTree.set_border_width(10)
        self.scrollTree.add_with_viewport(self.treeView)  
        self.scrollTree.set_size_request(400, 250)   
        self.treeView.show()
        self.scrollTree.show()   
        box.pack_start(self.scrollTree, True, False, 3)
        gobject.timeout_add(100, self.timeout)        
        
    def timeout(self):
        self.treeView.set_model(self.create_model())
        return True
    
    def fill_treeview(self):
        return None
    
    def create_model(self):
        return None
    
class MembersTable(UpdatingTable):    
    def __init__(self,box,c):
        UpdatingTable.__init__(self,box,c)        
        
    def fill_treeview(self):        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("IP", rendererText, text=0)
        column.set_sort_column_id(0)    
        self.treeView.append_column(column)
        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", rendererText, text=1)
        column.set_sort_column_id(1)
        self.treeView.append_column(column)
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("LastSeen", rendererText, text=2)
        column.set_sort_column_id(2)
        self.treeView.append_column(column)
    
    def create_model(self):
        me = self.c.get_members()
        ti = self.c.get_member_timeout()
        st = gtk.ListStore(str, str, int)
        for ip in me.keys():
            member_entry=("","","")
            if(ti.has_key(ip)):
                member_entry = (ip,me[ip],int(time.time()-ti[ip]))
            else:
                member_entry = (ip,me[ip],-1)            
            st.append(member_entry)
        st.set_sort_column_id(2,gtk.SORT_DESCENDING)
        return st
    
class MessageTable(UpdatingTable):
    def __init__(self,box,c):
        UpdatingTable.__init__(self,box,c)     
        
    def fill_treeview(self):
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Time", rendererText, text=0)
        column.set_sort_column_id(0)    
        self.treeView.append_column(column)
        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Sender", rendererText, text=1)
        column.set_sort_column_id(1)
        self.treeView.append_column(column)
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Message", rendererText, text=2)
        column.set_sort_column_id(2)
        self.treeView.append_column(column)
    
    def create_model(self):
        m = self.c.get_last_msgs(None)
        st = gtk.ListStore(str, str, str)
        for i in m:
            if i[1] in self.c.get_members():
                i=(time.strftime("%a, %d.%m.%Y %H:%M:%S", i[0]),self.c.get_members()[i[1]],i[2])
            else:
                i=(time.strftime("%a, %d.%m.%Y %H:%M:%S", i[0]),i[1],i[2])
            st.append(i)
        return st
        
        
    
def msg_window(w, c):    
    c.reset_new_msgs() 
    
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)

    window.set_border_width(10)
    window.set_position(gtk.WIN_POS_CENTER)
    window.set_title("Lunchinator")
    
    box1 = gtk.VBox(False, 0)
    box2 = gtk.HBox(False, 0)    
    msgt = MessageTable(box2,c)    
    memt = MembersTable(box2,c)
    box1.pack_start(box2, False, False, 0)
    if c.ls.show_pic_url:
        try:
            #todo disable proxy for now
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            response=opener.urlopen(c.ls.show_pic_url)
            loader=gtk.gdk.PixbufLoader()
            loader.write(response.read())
            loader.close()     
            gtkimage = gtk.Image() 
            gtkimage.set_from_pixbuf(loader.get_pixbuf())
            gtkimage.show()
            box2.pack_start(gtkimage, True, True, 0)
        except:
            pass
    box2.show()
    
    box2 = gtk.HBox(False, 0)
    entry = gtk.Entry()    
    box2.pack_start(entry, True, True, 0)
    entry.show()
    button = gtk.Button("Send Msg")
    box2.pack_start(button, True, False, 0)
    button.show()
    
#    box1.pack_start(box2, False, False, 0)
#    box2.show()
#        
#    box2 = gtk.HBox(False, 0)
    entry2 = gtk.Entry()    
    box2.pack_start(entry2, True, True, 0)
    entry2.show()
    button2 = gtk.Button("Add Host")
    box2.pack_start(button2, True, False, 0)
    button2.show()
    
    box1.pack_start(box2, False, False, 0)
    box2.show()
    
    window.add(box1)   
    box1.show()
    window.show()
    entry.connect("activate", send_msg, c)
    entry.connect_object("activate", gtk.Widget.destroy, window)
    button.connect_object("clicked", gtk.Widget.activate, entry)
    entry2.connect("activate", add_host, c)
    button2.connect_object("clicked", gtk.Widget.activate, entry2) 
