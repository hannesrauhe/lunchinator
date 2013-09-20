import sys,types
import gobject
import gtk
from lunchinator import get_server
import time, socket,logging,threading,os
import platform
import urllib2
import traceback    
from StringIO import StringIO   
        
class lunchinator(threading.Thread):
    _menu = None
    
    def __init__(self, noUpdates = False):           
        threading.Thread.__init__(self)
        get_server().no_updates = noUpdates
        self.nb = None
    
    def run(self):
        get_server().start_server()   
        
    def getPlugins(self, cats):
        allPlugins = {}
        for p_cat in cats:
            for info in get_server().plugin_manager.getPluginsOfCategory(p_cat):
                allPlugins[info.name] = (p_cat, info.plugin_object)
        return allPlugins
           
    
    def init_menu(self):        
        #create the plugin submenu
        plugin_menu = gtk.Menu()
        
        usePrepend = False
        if platform.linux_distribution()[0] == "Ubuntu" and \
                (int(platform.linux_distribution()[1].split(".")[0])<10 or \
                 platform.linux_distribution()[1] == "10.04"):
            usePrepend = True
        
        allPlugins= self.getPlugins(['general','called','gui'])
        for pluginName in sorted(allPlugins.iterkeys()):
            p_item = gtk.CheckMenuItem(pluginName)            
            p_item.set_active(allPlugins[pluginName][1].is_activated)                
            p_item.connect("activate", self.toggle_plugin,allPlugins[pluginName][0])
            
            if usePrepend:
                plugin_menu.prepend(p_item)
            else:
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
        p_name = w.get_label()
        p_cat = data[0] 
        if w.get_active():
            po = get_server().plugin_manager.activatePluginByName(p_name,p_cat)
            if p_cat=="gui" and self.nb:
                #check if widget is already present
                alreadyShowing = False
                for i in range(len(self.nb)):
                    widget = self.nb.get_nth_page(i)
                    if self.nb.get_tab_label_text(widget) == p_name:
                        alreadyShowing = True
                if not alreadyShowing:
                    widget = self.window_msgCheckCreatePluginWidget(po,p_name)    
                    self.nb.append_page(widget, gtk.Label(p_name))
                    self.nb.set_tab_reorderable(widget, True)
                    self.nb.show()
                    self.nb.set_current_page(len(self.nb)-1)
        else:
            get_server().plugin_manager.deactivatePluginByName(p_name,p_cat)  
            if p_cat=="gui" and self.nb:
                alreadyShowing = False
                for i in range(len(self.nb)):
                    widget = self.nb.get_nth_page(i)
                    if self.nb.get_tab_label_text(widget) == p_name:
                        self.nb.remove_page(i)
                        break
        get_server().write_config_to_hd()
        
    def stop_server(self,_):        
        if self.isAlive():
            get_server().running = False
            self.join()  
            print "server stopped" 
        else:
            print "server not running"
    
    def check_new_msgs(self):
        return get_server().new_msg
    
    def reset_new_msgs(self):
        get_server().new_msg=False
        
    def disable_auto_update(self):
        get_server().auto_update=False
                  
    def quit(self,w): 
        self.stop_server(w)
        os._exit(0)     
      
    def window_msgCheckCreatePluginWidget(self,plugin_object,p_name):
        sw = None
        try:
            sw = plugin_object.create_widget()
        except:
            stringOut = StringIO()
            traceback.print_exc(None, stringOut)
            get_server().lunch_logger.exception("while including plugin %s with options: %s  %s"%(p_name, str(plugin_object.options), str(sys.exc_info())))
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            textview = gtk.TextView()
            textview.set_size_request(400,200)
            textview.set_wrap_mode(gtk.WRAP_WORD)
            textbuffer = textview.get_buffer()
            sw.add(textview)
            sw.show()
            textview.show()
            
            textbuffer.set_text(stringOut.getvalue())
            stringOut.close() 
        return sw
        
    def window_msg(self, _):    
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
        msgt = MessageTable()
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
        memt = MembersTable()
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
            for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    plugin_widgets.append((pluginInfo,self.window_msgCheckCreatePluginWidget(pluginInfo.plugin_object,pluginInfo.name)))
            if len(plugin_widgets) == 0:
                #activate help plugin
                get_server().plugin_manager.activatePluginByName("About Plugins", "gui")
                pluginInfo = get_server().plugin_manager.getPluginByName("About Plugins", "gui")
                if pluginInfo != None:
                    plugin_widgets.append((pluginInfo,self.window_msgCheckCreatePluginWidget(pluginInfo.plugin_object,pluginInfo.name)))
                pass                    
        except:
            get_server().lunch_logger.exception("while including plugins %s"%str(sys.exc_info()))
            
        plugin_widgets.sort(key=lambda tup: tup[0].name)
        plugin_widgets.sort(key=lambda tup: tup[0].plugin_object.sortOrder)
        
        self.nb = gtk.Notebook()
        self.nb.set_tab_pos(gtk.POS_TOP)
        for info,widget in plugin_widgets:
            self.nb.append_page(widget, gtk.Label(info.name))
            self.nb.set_tab_reorderable(widget, True)
        
        # select previously selected widget
        index = 0
        if get_server().last_gui_plugin_index < len(self.nb) and get_server().last_gui_plugin_index >= 0:
            index = get_server().last_gui_plugin_index
        
        self.nb.show()
        self.nb.set_current_page(index)
        box0.pack_start(self.nb, True, True, 0)
        box0.show()
        
        window.add(box0)
        window.show()
        entry.connect("activate", self.clicked_send_msg)
        button.connect_object("clicked", gtk.Widget.activate, entry)
        entry2.connect("activate", self.clicked_add_host)
        button2.connect_object("clicked", gtk.Widget.activate, entry2)
        window.connect("delete-event", self.window_msgClosed)      
            
    def window_msgClosed(self, _, *__):
        try:
            order = []
            for i in range(len(self.nb)):
                widget = self.nb.get_nth_page(i)
                order.append(self.nb.get_tab_label_text(widget))
            for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.name in order:
                    pluginInfo.plugin_object.sortOrder = order.index(pluginInfo.name)
                    pluginInfo.plugin_object.save_sort_order()
                    
            if self.nb != None:
                get_server().set_last_gui_plugin_index(self.nb.get_current_page())
        except:
            get_server().lunch_logger.error("while storing order of GUI plugins:\n  %s", str(sys.exc_info()))
        self.nb = None
            
    def clicked_send_msg(self,w,*data):
        if len(data):
            get_server().call_all_members(data[0])
        else:
            get_server().call_all_members(w.get_text())
            w.set_text("")
        
    def clicked_add_host(self,w):
        hostn = w.get_text()
        try:
            get_server().members[socket.gethostbyname(hostn.strip())]=hostn.strip()
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
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    try:
                        w = pluginInfo.plugin_object.create_options_widget()
                        if w:
                            plugin_widgets.append((pluginInfo.name,w))
                    except:
                        plugin_widgets.append((pluginInfo.name,gtk.Label("Error while including plugin")))
                        get_server().lunch_logger.exception("while including plugin %s in settings window: %s",pluginInfo.name, str(sys.exc_info()))
        except:
            get_server().lunch_logger.exception("while including plugins in settings window: %s", str(sys.exc_info()))
        plugin_widgets.sort(key=lambda aTuple: "" if aTuple[0] == "General Settings" else aTuple[0])
        for name,widget in plugin_widgets:
            nb.append_page(widget,gtk.Label(name))
        nb.show_all()
        d.get_content_area().pack_start(nb, True, True, 0)
        if len(nb) > 0:
            nb.set_current_page(0)
        resp = d.run()
        
        #save on exit
        
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                if resp==gtk.RESPONSE_APPLY:
                    try:
                        pluginInfo.plugin_object.save_options_widget_data()
                    except:
                        get_server().lunch_logger.error("was not able to save data for plugin %s: %s",pluginInfo.name, str(sys.exc_info()))
                else:
                    pluginInfo.plugin_object.discard_options_widget_data()
            
        d.destroy()
        get_server().send_info_around()

        

class UpdatingTable(object):
    def __init__(self):
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
    def __init__(self):
        UpdatingTable.__init__(self)        
        
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
        me = get_server().get_members()
        ti = get_server().get_member_timeout()
        inf = get_server().get_member_info()
        self.listStore.clear()
        for ip in me.keys():
            member_entry=[ip,me[ip],"-",-1,"#FFFFFF"]
            if inf.has_key(ip) and inf[ip].has_key("next_lunch_begin") and inf[ip].has_key("next_lunch_end"):
                member_entry[2]=inf[ip]["next_lunch_begin"]+"-"+inf[ip]["next_lunch_end"]  
                if get_server().is_now_in_time_span(inf[ip]["next_lunch_begin"],inf[ip]["next_lunch_end"]):
                    member_entry[4]="#00FF00"
                else:
                    member_entry[4]="#FF0000"
            if ti.has_key(ip):
                member_entry[3]=int(time.time()-ti[ip])        
            self.listStore.append(tuple(member_entry))
    
class MessageTable(UpdatingTable):
    def __init__(self):
        UpdatingTable.__init__(self)     
        
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
        m = get_server().get_last_msgs()
        self.listStore.clear()
        for i in m:
            if i[1] in get_server().get_members():
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),get_server().get_members()[i[1]],i[2])
            else:
                i=(time.strftime("%d.%m.%Y %H:%M:%S", i[0]),i[1],i[2])
            self.listStore.append(i)
        return self.listStore
    
