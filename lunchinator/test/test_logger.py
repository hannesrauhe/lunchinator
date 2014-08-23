# -*- coding: utf-8 -*-
from lunchinator.log import getCoreLogger, initializeLogger
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
getCoreLogger().info("Test")
# log unicode string
getCoreLogger().info(u"Test")
# log unicode string with special characters
getCoreLogger().info(u"Testäöüß")
# log utf-8 string with special characters
getCoreLogger().info(u"Testäöüß".encode("utf-8"))
# log strings with arguments containing special characters
getCoreLogger().info(u"Testäöü %s %s", u"äöüß", u"äöüß")
getCoreLogger().info("Test %s %s", u"äöüß", u"äöüß")
# log string with str argument containing special characters (not possible using default logger class)
getCoreLogger().info("Wow, this works now! %s %s", u"äöüß", u"äöüß".encode("utf-8"))

sig = SignalTest()
sig.s.connect(sig.testSlot, type=Qt.DirectConnection)
sig.s.connect(partial(sig.testSlotArg, 42))
sig.emitSignal()
