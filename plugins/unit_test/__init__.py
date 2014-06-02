from lunchinator.iface_plugins import iface_called_plugin
from lunchinator import get_server, get_settings, get_peers, \
  get_notification_center, log_exception, log_error, log_warning
from lunchinator.utilities import displayNotification
from PyQt4.QtGui import QTextEdit
import json

class unit_test(iface_called_plugin):
    def __init__(self):
        super(unit_test, self).__init__()
        
    def process_event(self, cmd, value, ip, member_info):
        if cmd == "HELO_SELFTEST":
            import unittest
            from notificationCenter import notificationCenterTestCase
            runner = unittest.TextTestRunner()
            
            log_warning("Starting SelfTest")
            suite = unittest.makeSuite(notificationCenterTestCase,'test')
            runner.run(suite)
