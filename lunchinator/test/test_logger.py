# -*- coding: utf-8 -*-
from lunchinator.log import getCoreLogger, initializeLogger
from PyQt4.QtCore import QObject, pyqtSignal, Qt, pyqtSlot
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.log.lunch_logger import newLogger
from lunchinator.log.logging_func import loggingFunc
from pkg_resources import get_distribution

get_distribution("python-twjitter > 23.0")

class SignalTest(QObject):
    s = pyqtSignal()
    
    def __init__(self):
        super(SignalTest, self).__init__()
        self.logger = newLogger("test")
    
    def emitSignal(self):
        self.s.emit()
    
    @loggingFunc
    def testFunc(self):
        raise ValueError("From loggingFunc")
        
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
#sig.s.connect(sig.testSlot, type=Qt.DirectConnection)
sig.s.connect(sig.testFunc, type=Qt.DirectConnection)
#sig.s.connect(partial(sig.testSlotArg, 42))
sig.emitSignal()


from PyQt4.QtCore import QThread
from PyQt4.QtGui import QApplication
from functools import partial
import threading
class FooClass(QObject):
    fooS = pyqtSignal(unicode)
    @loggingSlot(unicode)
    def foo(self, i, s):
        for _ in range(3):
            QThread.sleep(1)
            print i, str(s.toUtf8()).encode('utf-8').strip(), threading.currentThread().ident
import sys
app = QApplication(sys.argv)

thread = QThread()
scanner = FooClass()
scanner.moveToThread(thread)
thread.start()

scanner.fooS.connect(partial(scanner.foo, 1))

print "enter text and check if it  appears immediately after you Enter:"

while True:
    line = sys.stdin.readline()
    print "you entered", line, threading.currentThread().ident
    scanner.fooS.emit(line)

sys.exit(0)