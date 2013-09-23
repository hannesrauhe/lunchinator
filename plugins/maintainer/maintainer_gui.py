import gtk,time,gobject
from lunchinator import get_server
import os

class maintainer_gui(object):
    def __init__(self,mt):
        self.entry = None
        self.but = None
        self.info_table = None
        self.mt = mt
        self.shown_logfile = get_server().log_file
        
    def display_report(self,w):
        if self.dropdown_reports.get_active()>=0:
            self.entry.get_buffer().set_text(self.mt.reports[self.dropdown_reports.get_active()][2])
        
    def request_log(self,w):
        member = self.dropdown_members.get_active_text()
        #number_str = "" if self.numberchooser.get_value()==0 else ".%d"%self.numberchooser.get_value()
        if member:
            get_server().call("HELO_REQUEST_LOGFILE %d %s"%(get_server().tcp_port,int(self.numberchooser.get_value())),member)
            #no number_str here:
            self.shown_logfile = "%s/logs/%s.log%s"%(get_server().main_config_dir,member,"")
            
    def request_update(self,w):
        member = self.dropdown_members.get_active_text()
        if member:
            get_server().call("HELO_UPDATE from GUI",member)
        
    def show_logfile(self):
        fcontent = ""
        try:
            fhandler = open(self.shown_logfile,"r")
            fcontent = fhandler.read()
            fhandler.close()
        except Exception as e:
            fcontent = "File not ready: %s"%str(e)
        self.log_area.get_buffer().set_text(fcontent)
        
        if not (self.log_area.flags() & gtk.MAPPED):
            return False
        return True
            
    def create_reports_widget(self):
        self.entry = gtk.TextView()
        self.entry.set_size_request(400,200)
        self.entry.set_wrap_mode(gtk.WRAP_WORD)
        self.entry.set_editable(False)
        frame = gtk.Frame()
        frame.add(self.entry)
        
        self.dropdown_reports = gtk.combo_box_new_text()
        for r in self.mt.reports:
            self.dropdown_reports.append_text("%s - %s"%(time.strftime("%a, %d %b %Y %H:%M:%S",time.localtime(r[0])),r[1]))
        self.dropdown_reports.set_active(0)
        
        memtVBox = gtk.VBox()        
        memtVBox.pack_start(self.dropdown_reports, False, False,5)
        descAlign = gtk.Alignment(0, 0, 0, 0)
        descAlign.add(gtk.Label("Description:"))
        memtVBox.pack_start(descAlign, False, True,0)
        memtVBox.pack_start(frame, True, True, 0)
        
        self.dropdown_reports.connect_object("changed", self.display_report,self.dropdown_reports)
        
        return memtVBox
    
    def create_into_table_widget(self):
        self.info_table = InfoTable()
        return self.info_table.scrollTree
                
    def create_logs_widget(self):
        self.log_area = gtk.TextView()
        self.log_area.set_size_request(400,200)
        self.log_area.set_wrap_mode(gtk.WRAP_WORD)
        self.log_area.set_editable(False)
        frame = gtk.Frame()
        frame.add(self.log_area)
        
        self.dropdown_members = gtk.combo_box_new_text()
        for m_ip,m_name in get_server().get_members().items():
            self.dropdown_members.append_text(m_ip)
            
        self.numberchooser = gtk.SpinButton(gtk.Adjustment(value=0, lower=0, upper=10, step_incr=1, page_incr=0, page_size=0))
        self.update_button = gtk.Button("Send Update Command")
        
        memHBox = gtk.HBox()
        memHBox.pack_start(self.dropdown_members, False, False, 5)
        memHBox.pack_start(self.numberchooser, False, False, 5)
        memHBox.pack_start(self.update_button, False, False, 5)
        
        memtVBox = gtk.VBox()    
        memtVBox.pack_start(memHBox, False, False, 5)
        memtVBox.pack_start(frame, True, True, 10)
        memtVBox.show_all()
        
        self.dropdown_members.connect_object("changed", self.request_log,self.dropdown_members)
        self.numberchooser.connect_object("changed", self.request_log,self.dropdown_members)
        self.update_button.connect_object("clicked", self.request_update,self.update_button)
        
        gobject.timeout_add(2000, self.show_logfile) 
        return memtVBox
    
    def create_widget(self):
        reports_widget = self.create_reports_widget()
        logs_widget = self.create_logs_widget()
        info_table_widget = self.create_into_table_widget()
        
        nb = gtk.Notebook()
        nb.set_tab_pos(gtk.POS_LEFT)
        nb.append_page(reports_widget, gtk.Label("Bug Reports"))
        nb.append_page(logs_widget, gtk.Label("Logs"))
        nb.append_page(info_table_widget, gtk.Label("Info"))
        nb.show_all()
        nb.set_current_page(0)
        
        return nb
    
    def updateInfoTable(self):
        if self.info_table != None:
            self.info_table.update_model()

class InfoTable(object):
    def __init__(self):
        self.listStore = None
        self.listStoreNumColumns = 0
        self.treeView = gtk.TreeView()
        self.scrollTree = gtk.ScrolledWindow()
        self.scrollTree.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrollTree.set_border_width(5)
        self.scrollTree.add_with_viewport(self.treeView)  
        self.scrollTree.set_size_request(400, 350)   
        self.treeView.show()
        self.scrollTree.show()   
        self.update_model()
    
    def update_model(self):
        if len(get_server().member_info) == 0:
            return
        
        table_data = {"ip":[""]*len(get_server().member_info)}
        index = 0
        for ip,infodict in get_server().member_info.iteritems():
            table_data["ip"][index] = ip
            for k,v in infodict.iteritems():
                if not table_data.has_key(k):
                    table_data[k]=[""]*len(get_server().member_info)
                if False:#k=="avatar" and os.path.isfile(get_server().avatar_dir+"/"+v):
                    # TODO add avatar image
                    table_data[k][index]="avatars/%s"%v
                else:
                    table_data[k][index]=v
            index+=1
        
        if self.listStore == None or self.listStoreNumColumns != len(table_data):
            # columns added/removed
            self.listStore = gtk.ListStore(*[str]*len(table_data))
            self.treeView.set_model(self.listStore)
            self.listStoreNumColumns = len(table_data)
        else:
            self.listStore.clear()
        
        rendererText = gtk.CellRendererText()
        for num, th in enumerate(table_data.iterkeys()):
            column = gtk.TreeViewColumn(th, rendererText, text=num)
            column.set_sort_column_id(num)
            self.treeView.append_column(column)
            
        for i in range(0,len(get_server().member_info)):
            row = []
            for k in table_data.iterkeys():
                row.append(table_data[k][i])
            self.listStore.append(row)
    
def main():
    # enter the main loop
    gtk.main()
    return 0

def WindowDeleteEvent(_, __):
    # return false so that window will be destroyed
    return False

def WindowDestroy(_, *__):
    # exit main loop
    gtk.main_quit()
    
class maintainer_wrapper:
    reports = []
    
if __name__ == "__main__":
    
    # create the top level window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_title("Layout Example")
    window.set_default_size(300, 300)
    window.connect("delete-event", WindowDeleteEvent)
    window.connect("destroy", WindowDestroy)
    
    window.add(maintainer_gui(maintainer_wrapper()).create_widget())
    
    # show all the widgets
    window.show_all()
    
    main()
