from lunchinator import log_exception, log_warning, log_debug
import inspect, sys
from functools import partial
from PyQt4.QtCore import QThread, pyqtSignal

def getArgSpec(aCallable):
    if inspect.isfunction(aCallable):
        argSpec = inspect.getargspec(aCallable)
        numArgs = len(argSpec.args)
    elif inspect.ismethod(aCallable):
        argSpec = inspect.getargspec(aCallable)
        numArgs = len(argSpec.args) - 1
    else:
        argSpec = inspect.getargspec(aCallable.__call__)
        numArgs = len(argSpec.args) - 1
    return (argSpec, numArgs)
    
def takesOneArgument(aCallable):
    if type(aCallable) == partial:
        log_debug("Warning: Cannot determine number of possible arguments for partial object.")
        return True
    argSpec, numArgs = getArgSpec(aCallable)
    
    minArgs = numArgs
    if argSpec.defaults != None:
        minArgs -= len(argSpec.defaults)
    if minArgs > 1 or (numArgs < 1 and argSpec.varargs == None):
        return False
    return True

def assertTakesOneArgument(aCallable):
    if type(aCallable) == partial:
        log_debug("Warning: Cannot determine number of possible arguments for partial object.")
        return
    if not takesOneArgument(aCallable):
        argSpec, _ = getArgSpec(aCallable)
        raise Exception("Not callable with exactly one argument: %s" % str(argSpec))  

class CallBase(object):
    def __init__(self, call, successCall, errorCall, mutex):
        super(CallBase, self).__init__()
        
        self._success = None
        self._error = None
        
        if successCall != None:
            if type(successCall) in (str, unicode):
                successCall = partial(log_warning, successCall)
            assertTakesOneArgument(successCall)
            self.setSuccessCall(successCall)
        if errorCall != None:
            if type(errorCall) in (str, unicode):
                errorCall = partial(log_warning, errorCall)            
            assertTakesOneArgument(errorCall)
            self.setErrorCall(errorCall)
        
        self._call = call
        self._mutex = mutex
        
    def setSuccessCall(self, successCall):
        self._success = successCall
        
    def setErrorCall(self, errorCall):
        self._error = errorCall
        
    def processCall(self, prevResult = None):
        try:
            if takesOneArgument(self._call):
                if self._mutex != None:
                    self.mutex.lock()
                try:
                    result = self._call(prevResult)
                finally:
                    if self._mutex != None:
                        self._mutex.release()
            else:
                if self._mutex != None:
                    self.mutex.lock()
                try:
                    result = self._call()
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
        
        :param call: The callable to be called, must be callable with zero or one argument.
                     If callable with one argument, the argument passed to __call__ will be forwarded to the callable.
        :param successCall: If call() does not raise an exception, successCall is called with the result of call().
        :param errorCall: If call() raises an exception, errorCall is called with an error message as the only argument.
        :param mutex: A QMutex object that will be locked during call().
        """
        super(SyncCall, self).__init__(call, successCall, errorCall, mutex)
        
    def __call__(self, prevResult = None):
        self.processCall(prevResult)
        
class AsyncCall(QThread, CallBase):
    success = pyqtSignal(object)
    error = pyqtSignal(unicode)
    
    def __init__(self, parent, call, successCall = None, errorCall = None, mutex = None):
        """
        Creates an asynchronous call object
        
        :param parent: The parent object for QThread.
        :param call: The callable to be called, must be callable with zero or one argument.
                     If callable with one argument, the argument passed to __call__ will be forwarded to the callable.
        :param successCall: If call() does not raise an exception, successCall is called with the result of call().
        :param errorCall: If call() raises an exception, errorCall is called with an error message as the only argument.
        :param mutex: A QMutex object that will be locked during call().
        """
        QThread.__init__(self, parent)
        CallBase.__init__(self, call, successCall, errorCall, mutex)
        self._prevResult = None

    def setErrorCall(self, errorCall):
        self.error.connect(errorCall)
        
    def setSuccessCall(self, successCall):
        self.success.connect(successCall)
        
    def callSuccess(self, result):
        self.success.emit(result)
        
    def callError(self, errorMessage):
        self.error.emit(errorMessage)

    def __call__(self, prevResult = None):
        self._prevResult = prevResult
        self.start()

    def run(self):
        self.processCall(self._prevResult)
        
if __name__ == '__main__':
    getArgSpec(partial(partial(int, base=2)))