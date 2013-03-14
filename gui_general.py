import sys,types
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
        settings_item = gtk.MenuItem("More Settings")
        
        debug_item.set_active(self.ls.get_debug())
        avatar_item.set_active(len(self.ls.get_avatar())>0)
            
        debug_item.connect("activate", self.toggle_debug_mode)
        avatar_item.connect("activate", self.window_select_avatar)
        settings_item.connect("activate",self.window_settings)        
                
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

        # Contains box1 and plug-ins
        box0 = gtk.HBox(False, 0)

        tablesPane = gtk.HPaned()
        
        # create HBox in VBox for each table
        # Create message table
        msgtVBox = gtk.VBox()
        msgtHBox = gtk.HBox()
        msgt = MessageTable(self.ls)
        msgtVBox.pack_start(msgt.scrollTree, True, True, 0)
        
        entry = gtk.Entry()    
        msgtHBox.pack_start(entry, True, True, 3)
        entry.show()
        button = gtk.Button("Send Msg")
        msgtHBox.pack_start(button, False, True, 10)
        button.show()
        msgtVBox.pack_start(msgtHBox, False, True, 0)
        msgtHBox.show()

        tablesPane.add1(msgtVBox)
        msgtVBox.show()

        # Create members table
        memtVBox = gtk.VBox()
        memtHBox = gtk.HBox()
        memt = MembersTable(self.ls)
        memtVBox.pack_start(memt.scrollTree, True, True, 0)

        entry2 = gtk.Entry()    
        memtHBox.pack_start(entry2, True, True, 3)
        entry2.show()
        button2 = gtk.Button("Add Host")
        memtHBox.pack_start(button2, False, True, 10)
        button2.show()
        memtVBox.pack_start(memtHBox, False, True, 0)
        memtHBox.show()
        
        tablesPane.add2(memtVBox)
        memtVBox.show()

        box0.pack_start(tablesPane, True, True, 0)
        tablesPane.show()
        
        plugin_widgets = []
        try:
            for pluginInfo in self.ls.plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    plugin_widgets.append((pluginInfo.name,pluginInfo.plugin_object.create_widget()))
        except:
            print "error while including plugin", sys.exc_info()
        if len(plugin_widgets)==1:
            box0.size_allocate(gtk.gdk.Rectangle(0,0,100,100))
            box0.pack_start(plugin_widgets[0][1], True, True, 0)
        elif len(plugin_widgets)>1:
            nb = gtk.Notebook()
            nb.set_tab_pos(gtk.POS_TOP)
            for name,widget in plugin_widgets:
                nb.append_page(widget,gtk.Label(name))
                nb.set_tab_reorderable(widget, True)
            nb.show()
            box0.pack_start(nb, True, True, 0)
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
            
    def window_settings(self,w):
        self.reset_new_msgs()        
                
        d = gtk.Dialog(title="Lunchinator Settings",buttons=("Save",gtk.RESPONSE_APPLY,"Cancel",gtk.RESPONSE_CANCEL))
        nb = gtk.Notebook()
        nb.set_tab_pos(gtk.POS_LEFT)
        options = ['user_name','audio_file','auto_update',"default_lunch_begin","default_lunch_end","alarm_begin_time","alarm_end_time","mute_timeout"]
        t = gtk.Table(len(options),2,True)
        i=0
        for o in options:
            methodname = "get_"+o
            v = ""
            e = ""
            if hasattr(self.ls, methodname): 
                _member = getattr(self.ls, methodname)
                v = _member()
            if type(v)==types.IntType:
                adjustment = gtk.Adjustment(value=v, lower=0, upper=1000000, step_incr=1, page_incr=0, page_size=0)
                e = gtk.SpinButton(adjustment)
            elif type(v)==types.BooleanType:
                e = gtk.CheckButton()
                e.set_active(v)
            else:
                e = gtk.Entry()
                e.set_text(v)
            t.attach(gtk.Label(o),0,1,i,i+1)
            t.attach(e,1,2,i,i+1)
            i+=1
        nb.append_page(t,gtk.Label("General"))
            
        plugin_widgets=[]        
        try:
            for pluginInfo in self.ls.plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    plugin_widgets.append((pluginInfo.name,pluginInfo.plugin_object.create_options_widget()))
        except:
            print "error while including plugin", sys.exc_info()
        for name,widget in plugin_widgets:
            nb.append_page(widget,gtk.Label(name))
        nb.show_all()        
        warn_label1 = gtk.Label("NOT YET IMPLEMENTED")
        warn_label1.show()
        warn_label2 = gtk.Label("Options will go here - change $HOME/.lunchinator/settings.cfg manually for now")
        warn_label2.show()
        d.get_content_area().pack_start(warn_label1, True, True, 0)
        d.get_content_area().pack_start(warn_label2, True, True, 0)
        d.get_content_area().pack_start(nb, True, True, 0)
        resp = d.run()
        d.destroy()
        

class UpdatingTable(object):
    listStore = None
    def __init__(self,ls):
        self.ls = ls
        self.listStore = self.create_model()
        self.update_model()
        self.treeView = gtk.TreeView(self.listStore)
        self.fill_treeview()
        self.scrollTree = gtk.ScrolledWindow()
        self.scrollTree.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollTree.set_border_width(5)
        self.scrollTree.add_with_viewport(self.treeView)  
        self.scrollTree.set_size_request(400, 350)   
        self.treeView.show()
        self.scrollTree.show()   
        gobject.timeout_add(1000, self.timeout)        
        
    def timeout(self):
        try:
            sortCol,sortOrder = self.treeView.get_model().get_sort_column_id()
            self.update_model()
            #if sortCol!=None:
              #  st.set_sort_column_id(sortCol,sortOrder)
            #self.treeView.set_model(self.listStore)
            return True
        except:
            return False
    
    def fill_treeview(self):
        return None
    
    def create_model(self):
        return None
    
    def update_model(self):
        pass
    
class MembersTable(UpdatingTable):    
    def __init__(self,ls):
        UpdatingTable.__init__(self,ls)        
        
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
        column = gtk.TreeViewColumn("LunchTime", rendererText, text=2, background=4)
        column.set_sort_column_id(2)
        self.treeView.append_column(column)
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("LastSeen", gtk.CellRendererText(), text=3)
        column.set_sort_column_id(3)
        self.treeView.append_column(column)
    
    def create_model(self):
        ls = gtk.ListStore(str, str, str, int, str)
        ls.set_sort_column_id(2,gtk.SORT_ASCENDING)
        return ls
    
    def update_model(self):
        me = self.ls.get_members()
        ti = self.ls.get_member_timeout()
        inf = self.ls.get_member_info()
        self.listStore.clear()
        for ip in me.keys():
            member_entry=[ip,me[ip],"-",-1,"#FFFFFF"]
            if inf.has_key(ip) and inf[ip].has_key("next_lunch_begin") and inf[ip].has_key("next_lunch_end"):
                member_entry[2]=inf[ip]["next_lunch_begin"]+"-"+inf[ip]["next_lunch_end"]  
                if self.ls.is_now_in_time_span(inf[ip]["next_lunch_begin"],inf[ip]["next_lunch_end"]):
                    member_entry[4]="#00FF00"
                else:
                    member_entry[4]="#FF0000"
            if ti.has_key(ip):
                member_entry[3]=int(time.time()-ti[ip])        
            self.listStore.append(tuple(member_entry))
    
class MessageTable(UpdatingTable):
    def __init__(self,ls):
        UpdatingTable.__init__(self,ls)     
        
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
        ls = gtk.ListStore(str, str, str)
        # TODO sort by date?
        #ls.set_sort_column_id(0,gtk.SORT_ASCENDING)
        return ls
    
    def update_model(self):
        m = self.ls.get_last_msgs()
        self.listStore.clear()
        for i in m:
            if i[1] in self.ls.get_members():
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),self.ls.get_members()[i[1]],i[2])
            else:
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),i[1],i[2])
            self.listStore.append(i)
        return self.listStore
        
if __name__ == "__main__":
    l = lunchinator()
    l.window_settings(None)
