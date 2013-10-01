#!/usr/bin/python
#
#in general you should use start_lunchinator.py in the root-directory to use the lunchinator
#
#this script can be used to start the lunchinator as GTK tray icon without self-updating functionality

import __preamble
from lunchinator.gui_controller import LunchinatorGuiController
from lunchinator.lunch_settings import lunch_options_parser
from PyQt4.QtGui import QApplication
import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
    
if __name__ == "__main__":
    (options, args) = lunch_options_parser().parse_args()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    lanschi = LunchinatorGuiController(options.noUpdates)

    sys.exit(app.exec_())
