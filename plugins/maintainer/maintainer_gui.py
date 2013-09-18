import gtk,time,gobject

class maintainer_gui(object):
    def __init__(self,mt):
        self.entry = None
        self.but = None
        self.mt = mt
        self.ls = mt.ls
        self.shown_logfile = self.ls.log_file
        
    def display_report(self,w):
        if self.dropdown_reports.get_active()>=0:
            self.entry.get_buffer().set_text(self.mt.reports[self.dropdown_reports.get_active()][2])
        
    def request_log(self,w):
        member = self.dropdown_members.get_active_text()
        #number_str = "" if self.numberchooser.get_value()==0 else ".%d"%self.numberchooser.get_value()
        if member:
            self.ls.call("HELO_REQUEST_LOGFILE %d %s"%(self.ls.tcp_port,int(self.numberchooser.get_value())),member)
            #no number_str here:
            self.shown_logfile = "%s/logs/%s.log%s"%(self.ls.main_config_dir,member,"")
            
    def request_update(self,w):
        member = self.dropdown_members.get_active_text()
        if member:
            self.ls.call("HELO_UPDATE from GUI",member)
        
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
            
    def create_widget(self):
        self.entry = gtk.TextView()
        self.entry.set_size_request(400,200)
        self.entry.set_wrap_mode(gtk.WRAP_WORD)
        if len(self.mt.reports):
            self.entry.get_buffer().set_text(str(self.mt.reports))
        
        self.log_area = gtk.TextView()
        self.log_area.set_size_request(400,200)
        self.log_area.set_wrap_mode(gtk.WRAP_WORD)
        
        self.dropdown_reports = gtk.combo_box_new_text()
        for r in self.mt.reports:
            self.dropdown_reports.append_text("%s - %s"%(time.strftime("%a, %d %b %Y %H:%M:%S",time.localtime(r[0])),r[1]))
        self.dropdown_reports.set_active(0)
                
        self.dropdown_members = gtk.combo_box_new_text()
        for m_ip,m_name in self.ls.get_members().items():
            self.dropdown_members.append_text(m_ip)
        
        self.numberchooser = gtk.SpinButton(gtk.Adjustment(value=0, lower=0, upper=10, step_incr=1, page_incr=0, page_size=0))
        self.update_button = gtk.Button("Send Update Command")
        memHBox = gtk.HBox()
        memHBox.pack_start(self.dropdown_members, False, False, 5)
        memHBox.pack_start(self.numberchooser, False, False, 5)
        memHBox.pack_start(self.update_button, False, False, 5)
        memtVBox = gtk.VBox()        
        memtVBox.pack_start(self.dropdown_reports, False, False,5)
        memtVBox.pack_start(gtk.Label("Description:"), False, False,5)
        memtVBox.pack_start(self.entry, False, True, 10)
        memtVBox.pack_start(memHBox, False, False, 5)
        memtVBox.pack_start(self.log_area, False, True, 10)
        memtVBox.show_all()
        self.dropdown_reports.connect_object("changed", self.display_report,self.dropdown_reports)
        self.dropdown_members.connect_object("changed", self.request_log,self.dropdown_members)
        self.numberchooser.connect_object("changed", self.request_log,self.dropdown_members)
        self.update_button.connect_object("clicked", self.request_update,self.update_button)
        
        gobject.timeout_add(2000, self.show_logfile) 
        return memtVBox
    
    
def main():
    # enter the main loop
    gtk.main()
    return 0

def WindowDeleteEvent(widget, event):
    # return false so that window will be destroyed
    return False

def WindowDestroy(widget, *data):
    # exit main loop
    gtk.main_quit()
    
if __name__ == "__main__":
    # create the top level window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_title("Layout Example")
    window.set_default_size(300, 300)
    window.connect("delete-event", WindowDeleteEvent)
    window.connect("destroy", WindowDestroy)
    
    window.add(maintainer_gui(None).create_widget())
    
    # show all the widgets
    window.show_all()
    
    main()
