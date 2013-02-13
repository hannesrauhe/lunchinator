#!/usr/bin/python
import appindicator
from gui_general import *
    
def highlight_icon(c):
#    if len(c.get_members())==0:
#        ind.set_status(appindicator.STATUS_PASSIVE)
    if c.check_new_msgs():
        ind.set_status(appindicator.STATUS_ATTENTION)
    else:
        ind.set_status(appindicator.STATUS_ACTIVE)
    return True
        
    
if __name__ == "__main__": 
    #you need this to use threads and GTK
    gobject.threads_init()
    
    icon_a = sys.path[0]+"/images/glyphicons_053_alarm.png"
    icon_b = sys.path[0]+"/images/glyphicons_053_alarm_red.png"
    global ind
    ind = appindicator.Indicator ("lunch notifier",
                                icon_a,
                                appindicator.CATEGORY_COMMUNICATIONS)
    ind.set_attention_icon(icon_b)
#    ind.set_icon_theme_path()
    ind.set_status (appindicator.STATUS_ACTIVE)
    #ind.set_attention_icon ("gksu-root-terminal")
    
    lanschi = lunchinator()
    #test_item = gtk.MenuItem("Test")
    #menu.append(test_item)      
    #test_item.connect("activate", highlight_icon)
    #test_item.show()
        
    ind.set_menu(lanschi.menu)
    
    gobject.timeout_add(2000, highlight_icon, lanschi.c)
    gtk.main()
