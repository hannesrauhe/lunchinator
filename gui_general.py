import sys,types
import gobject
import gtk
from lunchinator.lunch_server import *
import time, socket,logging,threading,os
from lunch_options import optionParser

import urllib2
                 
        
class lunchinator(threading.Thread):
    _menu = None
    ls = None
    
    def __init__(self, noUpdates = False):           
        threading.Thread.__init__(self)  
        self.ls = lunch_server(noUpdates)  
    
    def run(self):
        self.ls.start_server()      
    
    def init_menu(self):        
        #create the plugin submenu
        plugin_menu = gtk.Menu()
        for p_cat in ['general','called','gui']:
            for  info in self.ls.plugin_manager.getPluginsOfCategory(p_cat):
                p_item = gtk.CheckMenuItem(info.name)            
                p_item.set_active(info.plugin_object.is_activated)                
                p_item.connect("activate", self.toggle_plugin,p_cat)                    
                plugin_menu.append(p_item)
        plugin_menu.show_all()
        
        #main _menu
        self._menu = gtk.Menu()    
        menu_items = gtk.MenuItem("Call for lunch")
        msg_items = gtk.MenuItem("Show Lunchinator")
        settings_item = gtk.MenuItem("Settings")
        plugin_item = gtk.MenuItem("PlugIns")
        exit_item = gtk.MenuItem("Exit")
                
        menu_items.connect("activate", self.clicked_send_msg, "lunch")
        msg_items.connect("activate", self.window_msg)
        settings_item.connect("activate", self.window_settings)
        plugin_item.set_submenu(plugin_menu)
        exit_item.connect("activate", self.quit)
        
        menu_items.show()         
        msg_items.show()
        settings_item.show() 
        plugin_item.show() 
        exit_item.show()
        
        self._menu.append(menu_items)
        self._menu.append(msg_items)  
        self._menu.append(settings_item)
        self._menu.append(plugin_item)
        self._menu.append(exit_item) 
        return self._menu
            
    def toggle_plugin(self,w,*data):
        if w.get_active():
            self.ls.plugin_manager.activatePluginByName(w.get_label(),data[0])
        else:
            self.ls.plugin_manager.deactivatePluginByName(w.get_label(),data[0])  
        self.ls.write_config_to_hd()
        
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
                    try:
                        plugin_widgets.append((pluginInfo.name,pluginInfo.plugin_object.create_widget()))
                    except:
                        sw = gtk.ScrolledWindow()
                        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                        textview = gtk.TextView()
                        textview.set_size_request(400,200)
                        textview.set_wrap_mode(gtk.WRAP_WORD)
                        textbuffer = textview.get_buffer()
                        sw.add(textview)
                        sw.show()
                        textview.show()
                        textbuffer.set_text("Error while including plugin"+str(sys.exc_info()))                                      
                        plugin_widgets.append((pluginInfo.name,sw))
                        self.ls.lunch_logger.error("error while including plugin %s with options: %s  %s",pluginInfo.name, str(pluginInfo.plugin_object.options), str(sys.exc_info()))
        except:
            self.ls.lunch_logger.error("error while including plugins %s", str(sys.exc_info()))
        if len(plugin_widgets)==1:
            box0.size_allocate(gtk.gdk.Rectangle(0,0,100,100))
            box0.pack_start(plugin_widgets[0][1], True, True, 0)
        elif len(plugin_widgets)>1:
            nb = StoredOrderNotebook(["Webcam"])
            nb.set_tab_pos(gtk.POS_TOP)
            for name,widget in plugin_widgets:
                nb.insert_page_in_order(widget,name)
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
#        window.connect("delete-event",lambda w,x: sys.stdout.write(str(nb.get_order())+str(x)))      
            
    def clicked_send_msg(self,w,*data):
        if len(data):
            self.ls.call_all_members(data[0])
        else:
            self.ls.call_all_members(w.get_text())
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
            
        plugin_widgets=[]        
        try:
            for pluginInfo in self.ls.plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    try:
                        w = pluginInfo.plugin_object.create_options_widget()
                        if w:
                            plugin_widgets.append((pluginInfo.name,w))
                    except:
                        plugin_widgets.append((pluginInfo.name,gtk.Label("Error while including plugin")))
                        self.ls.lunch_logger.error("while including plugin %s in settings window: %s",pluginInfo.name, str(sys.exc_info()))
        except:
            self.ls.lunch_logger.error("error while including plugins in settings window: %s", str(sys.exc_info()))
        for name,widget in plugin_widgets:
            nb.append_page(widget,gtk.Label(name))
        nb.show_all()
        d.get_content_area().pack_start(nb, True, True, 0)
        resp = d.run()
        
        #save on exit
        
        for pluginInfo in self.ls.plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                if resp==gtk.RESPONSE_APPLY:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data()
                    except:
                        self.ls.lunch_logger.error("was not able to save data for plugin %s: %s",pluginInfo.name, str(sys.exc_info()))
                else:
                    pluginInfo.plugin_object.discard_options_widget_data()
            
        d.destroy()
        self.ls.send_info_around()

        

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
    
class StoredOrderNotebook(gtk.Notebook):
    order = []
    unorder = []
    def __init__(self,order):
        gtk.Notebook.__init__(self)
        self.order = order
    
    def insert_page_in_order(self, w, name):
        self.unorder.append(name)
        self.append_page(w, gtk.Label(name))
        
    def get_order(self):
        return self.order
        
if __name__ == "__main__":
    l = lunchinator()
    l.window_settings(None)
