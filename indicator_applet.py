#!/usr/bin/python
import appindicator,platform
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
    
    icon_a = "news-feed"
    icon_b = "gksu-root-terminal"
    if int(platform.linux_distribution()[1].split(".")[0])>=12:        
        icon_a = sys.path[0]+"/images/glyphicons_053_alarm.png"
        icon_b = sys.path[0]+"/images/glyphicons_053_alarm_red.png"
    
    global ind
    ind = appindicator.Indicator ("lunch notifier",
                                icon_a,
                                appindicator.CATEGORY_COMMUNICATIONS)
    ind.set_attention_icon(icon_b)
    ind.set_status (appindicator.STATUS_ACTIVE)
    
    lanschi = lunchinator()
    lanschi.start()
            
    ind.set_menu(lanschi.menu)
    
    gobject.timeout_add(2000, highlight_icon, lanschi)
    try:
        gtk.main()
    finally:
        lanschi.stop_server(None)
        os._exit(0)
