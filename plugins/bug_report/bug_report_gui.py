import gtk
from lunchinator import get_server

class bug_report_gui(object):
    def __init__(self):
        self.entry = None
        self.but = None
        
    def send_report(self,w):
        if get_server() and len(w.props.text):
            get_server().call("HELO_BUGREPORT_DESCR %s"%w.props.text)
        else:
            print "HELO_BUGREPORT_DESCR %s"%w.props.text
            
        self.entry.get_buffer().set_text("")
            
    def create_widget(self):
        self.entry = gtk.TextView()
        self.entry.set_size_request(400,200)
        self.entry.set_wrap_mode(gtk.WRAP_WORD)
        self.but = gtk.Button("Send Report")
        
        memtVBox = gtk.VBox()        
        memtVBox.pack_start(gtk.Label("Describe your problem:"), False, False,5)
        memtVBox.pack_start(self.entry, False, True, 10)
        memtVBox.pack_start(self.but, False, False, 5)
        self.entry.show()
        self.but.show()
        memtVBox.show()
        self.but.connect_object("clicked", self.send_report, self.entry.get_buffer())
        return memtVBox
    
#standalone

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
