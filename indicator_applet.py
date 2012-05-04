#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.
#
# Authors: Neil Jagdish Patel <neil.patel@canonical.com>
#          Jono Bacon <jono@ubuntu.com>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the 
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by 
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the applicable version of the GNU Lesser General Public 
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public 
# License version 3 and version 2.1 along with this program.  If not, see 
# <http://www.gnu.org/licenses/>
#

import gobject
import gtk
import appindicator
#import lunch_server
import lunch_client
import threading


def menuitem_response(w, buf):
    lunch_client.call("lunch")

if __name__ == "__main__": 
    #t1 = threading.Thread(target=lunch_server.start_server)
    #t1.start()
    #t1.join()
    ind = appindicator.Indicator ("lunch notifier",
                                "news-feed",
                                appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_status (appindicator.STATUS_ACTIVE)
    ind.set_attention_icon ("indicator-messages-new")
    
    # create a menu
    menu = gtk.Menu()    
    menu_items = gtk.MenuItem("Call for lunch")
    menu.append(menu_items)      
    menu_items.connect("activate", menuitem_response, "")
    menu_items.show()
    
    ind.set_menu(menu)
    
    gtk.main()
