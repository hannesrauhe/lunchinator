import gtk,time

class maintainer_gui(object):
    def __init__(self,mt):
        self.entry = None
        self.but = None
        self.mt = mt
        self.ls = mt.ls
        
    def display_report(self,w):
        if self.dropdown.get_active()>0:
            self.entry.get_buffer().set_text(self.mt.reports[self.dropdown.get_active()][2])
        
    def request_log(self,text):
        self.dropdown.get_active()
            
    def create_widget(self):
        self.entry = gtk.TextView()
        self.entry.set_size_request(400,200)
        self.entry.set_wrap_mode(gtk.WRAP_WORD)
        if len(self.mt.reports):
            self.entry.get_buffer().set_text(str(self.mt.reports))
        self.but = gtk.Button("Get Log")
        
        self.dropdown = gtk.combo_box_new_text()
        for r in self.mt.reports:
            self.dropdown.append_text("%s - %s"%(time.strftime("%a, %d %b %Y %H:%M:%S",time.localtime(r[0])),r[1]))
        self.dropdown.set_active(0)
        
        memtVBox = gtk.VBox()        
        memtVBox.pack_start(self.dropdown, False, False,5)
        memtVBox.pack_start(gtk.Label("Description:"), False, False,5)
        memtVBox.pack_start(self.entry, False, True, 10)
        memtVBox.pack_start(self.but, False, False, 5)
        self.dropdown.show()
        self.entry.show()
        self.but.show()
        memtVBox.show()
        self.dropdown.connect_object("changed",self.display_report,self.dropdown)
        self.but.connect_object("clicked", self.request_log,self.but)
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
    
    window.add(bug_report_gui(None).create_widget())
    
    # show all the widgets
    window.show_all()
    
    main()
