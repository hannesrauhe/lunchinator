""" taken from https://stackoverflow.com/questions/19078249/emit-signal-in-standard-python-thread"""

from PyQt4 import Qt, QtCore
import socket
import Queue
from PyQt4.Qt import QObject
from twisted.test.test_pb import callbackArgs

# Object of this class has to be shared between
# the two threads (Python and Qt one).
# Qt thread calls 'connect',   
# Python thread calls 'emit'.
# The slot corresponding to the emitted signal
# will be called in Qt's thread.
class SafeConnector(QObject):
    def __init__(self):
        super(SafeConnector, self).__init__()
        self._rsock, self._wsock = socket.socketpair()
        self._queue = Queue.Queue()
        self._qt_object = QtCore.QObject()
        self._notifier = QtCore.QSocketNotifier(self._rsock.fileno(),
                                                QtCore.QSocketNotifier.Read)
        self._notifier.activated.connect(self._recv)

    homeTimelineUpdated = QtCore.pyqtSignal(object)
    def connect_home_timeline_updated(self, callback):
        self.homeTimelineUpdated.connect(callback)
        
    def emit_home_timeline_updated(self):
        self._emit_from_threading(self.homeTimelineUpdated, None)

    twitterLoopStarted = QtCore.pyqtSignal(object)
    def connect_twitter_loop_started(self, callback):
        self.twitterLoopStarted.connect(callback)
        
    def emit_twitter_loop_started(self):
        self._emit_from_threading(self.twitterLoopStarted, None)

    twitterLoopStopped = QtCore.pyqtSignal(object)
    def connect_twitter_loop_stopped(self, callback):
        self.twitterLoopStopped.connect(callback)
        
    def emit_twitter_loop_stopped(self):
        self._emit_from_threading(self.twitterLoopStopped, None)
        
    rangeLimiteExceeded = QtCore.pyqtSignal(object)
    def connect_range_limit_exceeded(self, callback):
        self.twitterLoopStopped.connect(callback)
        
    def emit_range_limit_exceeded(self):
        self._emit_from_threading(self.rangeLimiteExceeded, None)
        
    updatePosted = QtCore.pyqtSignal(object)
    def connect_update_posted(self, callback):
        self.updatePosted.connect(callback)
        
    def emit_update_posted(self, postId):
        self._emit_from_threading(self.updatePosted, postId)
        
    notAuthenticated = QtCore.pyqtSignal(object)
    def connect_not_authenticated(self, callback):
        self.notAuthenticated.connect(callback)
        
    def emit_not_authenticated(self):
        self._emit_from_threading(self.notAuthenticated, None)

    # should be called by Python thread
    def _emit_from_threading(self, signal, args):
        self._queue.put((signal, args))
        self._wsock.send('!')

    # happens in Qt's main thread
    def _recv(self):
        self._rsock.recv(1)
        signal, args = self._queue.get()
        signal.emit(args)