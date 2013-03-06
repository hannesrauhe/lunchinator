import sys
import gobject
import gtk
import lunch_server
import lunch_client
import lunch_avatar
import time
import socket
import threading,os

import urllib2
                 
        
class lunchinator(threading.Thread):
    menu = None
    ls = lunch_server.lunch_server()
    lc = lunch_client.lunch_client()
    lanschi_http = None
    
    def __init__(self):           
        threading.Thread.__init__(self)    
        self.init_menu() 
    
    def run(self):
        self.ls.start_server()      
    
    def init_menu(self):
        #create the settings submenu
        settings_menu = gtk.Menu()
        avatar_item = gtk.CheckMenuItem("Avatar")
        debug_item = gtk.CheckMenuItem("Debug Output")
        settings_item = gtk.CheckMenuItem("More Settings")
        
        debug_item.set_active(self.ls.get_debug())
        avatar_item.set_active(len(self.ls.get_avatar())>0)
            
        debug_item.connect("activate", self.toggle_debug_mode)
        avatar_item.connect("activate", self.window_select_avatar)
                
        settings_menu.append(avatar_item)
        settings_menu.append(debug_item)
        settings_menu.append(settings_item)
        settings_menu.show_all()
        
        
        #create the plugin submenu
        plugin_menu = gtk.Menu()
        for p_cat in ['called','gui']:
            for  info in self.ls.plugin_manager.getPluginsOfCategory(p_cat):
                p_item = gtk.CheckMenuItem(info.name)            
                p_item.set_active(info.plugin_object.is_activated)                
                p_item.connect("activate", self.toggle_plugin,p_cat)                    
                plugin_menu.append(p_item)
        plugin_menu.show_all()
        
        #main menu
        self.menu = gtk.Menu()    
        menu_items = gtk.MenuItem("Call for lunch")
        msg_items = gtk.MenuItem("Show/Send messages")
        settings_item = gtk.MenuItem("Settings")
        plugin_item = gtk.MenuItem("PlugIns")
        exit_item = gtk.MenuItem("Exit")
                
        menu_items.connect("activate", self.clicked_send_msg, "lunch")
        msg_items.connect("activate", self.window_msg)
        settings_item.set_submenu(settings_menu)
        plugin_item.set_submenu(plugin_menu)
        exit_item.connect("activate", self.quit)
        
        menu_items.show()         
        msg_items.show()
        settings_item.show() 
        plugin_item.show() 
        exit_item.show()
        
        self.menu.append(menu_items)
        self.menu.append(msg_items)  
        self.menu.append(settings_item)
        self.menu.append(plugin_item)
        self.menu.append(exit_item) 
        
    def toggle_debug_mode(self,w):
        self.ls.set_debug(w.get_active())
            
    def toggle_plugin(self,w,*data):
#        p = self.ls.plugin_manager.getPluginByName(w.get_label(),data[0])
#        resp = p.plugin_object.show_options()
#        if resp == 1:
#            self.ls.plugin_manager.activatePluginByName(w.get_label(),data[0])
#        else:
#            self.ls.plugin_manager.deactivatePluginByName(w.get_label(),data[0])
#        w.set_active(resp)
        if w.get_active():
            self.ls.plugin_manager.activatePluginByName(w.get_label(),data[0])
        else:
            self.ls.plugin_manager.deactivatePluginByName(w.get_label(),data[0])
        
    def window_select_avatar(self,w):
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
    
    def check_new_msgs(self):
        return self.ls.new_msg
    
    def reset_new_msgs(self):
        self.ls.new_msg=False
        
    def disable_auto_update(self):
        self.ls.auto_update=False
                  
    def quit(self,w): 
        self.stop_server(w)
        os._exit(0)     
        
        
    def window_msg(self, w):    
        self.reset_new_msgs() 
        
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    
        window.set_border_width(10)
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_title("Lunchinator")

        box0 = gtk.HBox(False, 0)
        box1 = gtk.VBox(False, 0)
        box2 = gtk.HBox(False, 0)    
        msgt = MessageTable(box2,self.ls)    
        memt = MembersTable(box2,self.ls)
        box1.pack_start(box2, False, False, 0)
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
               
        box1.show()
        box0.pack_start(box1)
        try:
            for pluginInfo in self.ls.plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.add_horizontal(box0)
        except:
            print "error while including plugin", sys.exc_info()
        box0.show()
        
        window.add(box0)
        window.show()
        entry.connect("activate", self.clicked_send_msg)
        button.connect_object("clicked", gtk.Widget.activate, entry)
        entry2.connect("activate", self.clicked_add_host)
        button2.connect_object("clicked", gtk.Widget.activate, entry2)      
            
    def clicked_send_msg(self,w,*data):
        if len(data):
            self.lc.call(data[0],hosts=self.ls.get_members())
        else:
            self.lc.call(w.get_text())
            w.set_text("")
        
    def clicked_add_host(self,w):
        hostn = w.get_text()
        try:
            self.ls.members[socket.gethostbyname(hostn.strip())]=hostn.strip()
            w.set_text("")
        except:
            d = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=None)
            d.set_markup("Cannot add host: Hostname unknown")
            d.run()
            d.destroy()

class UpdatingTable(object):    
    def __init__(self,box,ls):
        self.ls = ls        
        self.treeView = gtk.TreeView(self.create_model())
        self.fill_treeview()
        self.scrollTree = gtk.ScrolledWindow()
        self.scrollTree.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollTree.set_border_width(10)
        self.scrollTree.add_with_viewport(self.treeView)  
        self.scrollTree.set_size_request(400, 350)   
        self.treeView.show()
        self.scrollTree.show()   
        box.pack_start(self.scrollTree, True, False, 3)
        gobject.timeout_add(1000, self.timeout)        
        
    def timeout(self):
        try:
            sortCol,sortOrder = self.treeView.get_model().get_sort_column_id()
            st = self.create_model()
            if sortCol!=None:
                st.set_sort_column_id(sortCol,sortOrder)
            self.treeView.set_model(st)
            return True
        except:
            return False
    
    def fill_treeview(self):
        return None
    
    def create_model(self):
        return None
    
class MembersTable(UpdatingTable):    
    def __init__(self,box,ls):
        UpdatingTable.__init__(self,box,ls)        
        
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
        me = self.ls.get_members()
        ti = self.ls.get_member_timeout()
        st = gtk.ListStore(str, str, int)
        for ip in me.keys():
            member_entry=("","","")
            if(ti.has_key(ip)):
                member_entry = (ip,me[ip],int(time.time()-ti[ip]))
            else:
                member_entry = (ip,me[ip],-1)            
            st.append(member_entry)
        st.set_sort_column_id(1,gtk.SORT_ASCENDING)
        return st
    
class MessageTable(UpdatingTable):
    def __init__(self,box,ls):
        UpdatingTable.__init__(self,box,ls)     
        
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
        m = self.ls.get_last_msgs()
        st = gtk.ListStore(str, str, str)
        for i in m:
            if i[1] in self.ls.get_members():
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),self.ls.get_members()[i[1]],i[2])
            else:
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),i[1],i[2])
            st.append(i)
        return st
        