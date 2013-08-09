import gtk
import string #fixed typo was using

class rot13box(object):
    def __init__(self):
        self.entry = gtk.Entry()  
        self.but = gtk.Button("ROT13")
        self.add_widget = None
        
    def encodeText(self,text):
        self.entry.set_text(text)
        self.enc(self.entry)
        
    def enc(self,w):        
        rot13 = string.maketrans( 
            "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz", 
            "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")
        plain = w.get_text()
        if plain:
            w.set_text(string.translate(plain, rot13))
        if self.add_widget:
            self.add_widget.show()
        
    def create_widget(self,additional_widget=None):  
        memtVBox = gtk.VBox()
        memtVBox.pack_start(self.entry, False, True, 10)
        memtVBox.pack_start(self.but, False, False, 10)
        if additional_widget:
            self.add_widget = additional_widget
            memtVBox.pack_start(self.add_widget, False, False, 10)
        self.entry.show()
        self.but.show()
        memtVBox.show()
        self.but.connect_object("clicked", self.enc, self.entry)
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
    
    window.add(rot13box().create_widget())
    
    # show all the widgets
    window.show_all()
    
    main()
