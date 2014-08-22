# -*- coding: utf-8 -*-
from lunchinator.log import getLogger, initializeLogger
from PyQt4.QtCore import QObject, pyqtSignal, Qt, pyqtSlot
from lunchinator.log.logging_slot import loggingSlot
from functools import partial

class SignalTest(QObject):
    s = pyqtSignal()
    
    def emitSignal(self):
        self.s.emit()
        
    @loggingSlot()
    def testSlot(self):
        raise ValueError("Test Error")
    
    @pyqtSlot(int)
    @loggingSlot()
    def testSlotArg(self, v=None):
        raise ValueError("Test Error %d" % v)
    
initializeLogger()

# log ascii string
getLogger().info("Test")
# log unicode string
getLogger().info(u"Test")
# log unicode string with special characters
getLogger().info(u"Testäöüß")
# log utf-8 string with special characters
getLogger().info(u"Testäöüß".encode("utf-8"))
# log strings with arguments containing special characters
getLogger().info(u"Testäöü %s %s", u"äöüß", u"äöüß")
getLogger().info("Test %s %s", u"äöüß", u"äöüß")
# log string with str argument containing special characters (not possible using default logger class)
getLogger().info("Wow, this works now! %s %s", u"äöüß", u"äöüß".encode("utf-8"))

sig = SignalTest()
sig.s.connect(sig.testSlot, type=Qt.DirectConnection)
sig.s.connect(partial(sig.testSlotArg, 42))
sig.emitSignal()
