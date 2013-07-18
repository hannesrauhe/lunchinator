#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as appindicator without self-updating functionality

import __preamble
import appindicator,platform,subprocess
from lunchinator.lunch_server import EXIT_CODE_UPDATE
from lunchinator.gui_general import *
    
def highlight_icon(c):
#    if len(c.get_members())==0:
#        ind.set_status(appindicator.STATUS_PASSIVE)
    if c.check_new_msgs():
        ind.set_status(appindicator.STATUS_ATTENTION)
    else:
        ind.set_status(appindicator.STATUS_ACTIVE)
    return True
        
    
if __name__ == "__main__": 
    (options, args) = lunch_options_parser().parse_args()
    
    #you need this to use threads and GTK
    gobject.threads_init()

    icon_a = None
    icon_b = None
    if not os.path.exists('/usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg') or \
       not os.path.exists('/usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg'):
        message = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO)
        message.set_markup("Do you want to install the Lunchinator icons into the Ubuntu theme folders? You will have to enter your sudo password.")
        gtkresponse = message.run()
        message.destroy()
        if gtkresponse==gtk.RESPONSE_YES:
            if subprocess.call(['gksudo', sys.path[0]+'/bin/install-lunch-icons.sh lunch'])==0:
                print "restarting after icons were installed"
                os._exit(EXIT_CODE_UPDATE)
            else:
                print "icons were not installed because of an error"
        
        if not os.path.exists('/usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg') or \
           not os.path.exists('/usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg'):
            # something went wrong - use old icons
            icon_a = "news-feed"
            icon_b = "gksu-root-terminal"
            if int(platform.linux_distribution()[1].split(".")[0])>=12:        
                icon_a = sys.path[0]+"/images/glyphicons_053_alarm.png"
                icon_b = sys.path[0]+"/images/glyphicons_053_alarm_red.png"
    else:
        icon_a = "lunchinator"
        icon_b = "lunchinatorred"
    
    global ind
    ind = appindicator.Indicator ("lunch notifier",
                                icon_a,
                                appindicator.CATEGORY_COMMUNICATIONS)
    ind.set_attention_icon(icon_b)
    ind.set_status (appindicator.STATUS_ACTIVE)
        
    lanschi = lunchinator(options.noUpdates)
    lanschi.start()
    lanschi.ls.init_done.wait()
            
    ind.set_menu(lanschi.init_menu())
    
    gobject.timeout_add(2000, highlight_icon, lanschi)
    try:
        gtk.main()
    finally:
        lanschi.stop_server(None)
        os._exit(0)
