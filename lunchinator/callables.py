from lunchinator import log_exception, log_warning, log_debug
import inspect, sys
from functools import partial
from PyQt4.QtCore import QThread, pyqtSignal

class CallBase(object):
    def __init__(self, call, successCall, errorCall, mutex):
        super(CallBase, self).__init__()
        
        self._success = None
        self._error = None
        
        if successCall != None:
            if type(successCall) in (str, unicode):
                successCall = partial(log_warning, successCall)
            self.setSuccessCall(successCall)
        if errorCall != None:
            if type(errorCall) in (str, unicode):
                errorCall = partial(log_warning, errorCall)            
            self.setErrorCall(errorCall)
        
        self._call = call
        self._mutex = mutex
        
    def setSuccessCall(self, successCall):
        self._success = successCall
        
    def setErrorCall(self, errorCall):
        self._error = errorCall
        
    def processCall(self, args, kwargs):
        try:
            if self._mutex != None:
                self.mutex.lock()
            try:
                result = self._call(*args, **kwargs)
            finally:
                if self._mutex != None:
                    self._mutex.release()
                
            self.callSuccess(result)
            return
        except:
            exc_info = sys.exc_info()
            typeName = u"Unknown Exception"
            if exc_info[0] != None:
                typeName = unicode(exc_info[0].__name__)
            errorMessage = u"%s: %s" % (typeName, unicode(exc_info[1]))
            log_exception(errorMessage)
        self.callError(errorMessage)
            
    def callError(self, errorMessage):
        if self._error != None:
            self._error(errorMessage)
        
    def callSuccess(self, result):
        if self._success != None:
            self._success(result)

class SyncCall(CallBase):
    def __init__(self, call, successCall = None, errorCall = None, mutex = None):
        """
        Creates a synchronous call object
        
        :param call: The callable to be called.
                     The arguments passed to __call__ will be forwarded to the callable.
        :param successCall: If call() does not raise an exception, successCall is called with the result of call().
        :param errorCall: If call() raises an exception, errorCall is called with an error message as the only argument.
        :param mutex: A QMutex object that will be locked during call().
        """
        super(SyncCall, self).__init__(call, successCall, errorCall, mutex)
        
    def __call__(self, *args, **kwargs):
        self.processCall(args, kwargs)
        
class AsyncCall(QThread, CallBase):
    success = pyqtSignal(object)
    error = pyqtSignal(unicode)
    
    def __init__(self, parent, call, successCall = None, errorCall = None, mutex = None):
        """
        Creates an asynchronous call object
        
        :param parent: The parent object for QThread.
        :param call: The callable to be called.
                     The arguments passed to __call__ will be forwarded to the callable.
        :param successCall: If call() does not raise an exception, successCall is called with the result of call().
        :param errorCall: If call() raises an exception, errorCall is called with an error message as the only argument.
        :param mutex: A QMutex object that will be locked during call().
        """
        QThread.__init__(self, parent)
        CallBase.__init__(self, call, successCall, errorCall, mutex)
        self._args = None
        self._kwargs = None

    def setErrorCall(self, errorCall):
        self.error.connect(errorCall)
        
    def setSuccessCall(self, successCall):
        self.success.connect(successCall)
        
    def callSuccess(self, result):
        self.success.emit(result)
        
    def callError(self, errorMessage):
        self.error.emit(errorMessage)

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self.start()

    def run(self):
        self.processCall(self._args, self._kwargs)
        
if __name__ == '__main__':
    getArgSpec(partial(partial(int, base=2)))