from lunchinator import log_exception, log_warning
import inspect
from functools import partial
from PyQt4.QtCore import QThread, pyqtSignal
from maintainer.github import GithubException

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
    argSpec, numArgs = getArgSpec(aCallable)
    
    minArgs = numArgs
    if argSpec.defaults != None:
        minArgs -= len(argSpec.defaults)
    if minArgs > 1 or (numArgs < 1 and argSpec.varargs == None):
        return False
    return True

def assertTakesOneArgument(aCallable):
    if not takesOneArgument(aCallable):
        argSpec, _ = getArgSpec(aCallable)
        raise Exception("Not callable with exactly one argument: %s" % str(argSpec))  

class CallBase(object):
    def __init__(self, call, successCall, errorCall, mutex):
        super(CallBase, self).__init__()
        
        if successCall != None:
            if type(successCall) in (str, unicode):
                successCall = partial(log_warning, successCall)
        if errorCall != None:
            if type(errorCall) in (str, unicode):
                errorCall = partial(log_warning, errorCall)
                        
        assertTakesOneArgument(successCall)
        assertTakesOneArgument(errorCall)
        
        self._call = call
        self._mutex = mutex
        self.setSuccessCall(successCall)
        self.setErrorCall(errorCall)
        
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
        except GithubException as e:
            if u'message' in e.data:
                errorMessage = u"GitHub Error: %s" % (e.data[u'message'])
            else:
                errorMessage = u"GitHub Error: %s" % unicode(e)
            log_warning(errorMessage)
        except:
            errorMessage = u"Exception during asynchronous call"
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
        super(SyncCall, self).__init__(call, successCall, errorCall, mutex)
        
    def __call__(self, prevResult = None):
        self.processCall(prevResult)
        
class AsyncCall(QThread, CallBase):
    success = pyqtSignal(object)
    error = pyqtSignal(unicode)
    
    def __init__(self, parent, call, successCall = None, errorCall = None, mutex = None):
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
        