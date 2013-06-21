#!/usr/bin/python
import appindicator,platform,subprocess
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
    
    if not os.path.exists('/usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg') or \
       not os.path.exists('/usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg'):
        subprocess.call(['gksudo', sys.path[0]+'/install-lunch-icons.sh lunch'])
    icon_a = "lunchinator"
    icon_b = "lunchinatorred"
    
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
    gtk.main()
