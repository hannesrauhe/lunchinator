#!/usr/bin/python
from gui_general import *
    
def highlight_icon(c):
    if c.check_new_msgs():
        statusicon.set_blinking(True)
    else:
        statusicon.set_blinking(False)
        
    return True
def show_menu(icon, button, time, menu):
    menu.show_all()
    menu.popup(None, None, gtk.status_icon_position_menu, button, time, statusicon)
    
if __name__ == "__main__":
    gobject.threads_init()
    lanschi = lunchinator()
    lanschi.c.disable_auto_update()

    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(sys.path[0]+"/images/glyphicons_053_alarm_black.png",25,25)
    global statusicon
    statusicon = gtk.StatusIcon()
    statusicon = gtk.status_icon_new_from_pixbuf(pixbuf)
    statusicon.connect("popup-menu", show_menu, lanschi.menu)
#    no double-click event
#    statusicon.connect("activate", msg_window, lanschi.c)
    
    gobject.timeout_add(2000, highlight_icon, lanschi.c)
    gtk.main()
