import sys
from functools import partial
from PyQt4.QtCore import QThread, pyqtSignal, QObject

class _CallBase(object):
    def __init__(self, call, successCall, errorCall, mutex, logger):
        super(_CallBase, self).__init__()
        
        self._success = None
        self._error = None
        self.logger = logger
        
        if successCall != None:
            if type(successCall) in (str, unicode):
                successCall = partial(self.logger.info, successCall)
            self._setSuccessCall(successCall)
        if errorCall != None:
            if type(errorCall) in (str, unicode):
                errorCall = partial(self.logger.warning, errorCall)            
            self._setErrorCall(errorCall)
        
        self._call = call
        self._mutex = mutex
        
    def _setSuccessCall(self, successCall):
        self._success = successCall
        
    def _setErrorCall(self, errorCall):
        self._error = errorCall
        
    def _processCall(self, args, kwargs):
        try:
            if self._mutex != None:
                self._mutex.lock()
            try:
                result = self._call(*args, **kwargs)
            finally:
                if self._mutex != None:
                    self._mutex.release()
                
            self._callSuccess(result)
            return
        except:
            exc_info = sys.exc_info()
            typeName = u"Unknown Exception"
            if exc_info[0] != None:
                typeName = unicode(exc_info[0].__name__)
            errorMessage = u"%s: %s" % (typeName, unicode(exc_info[1]))
            self.logger.exception(errorMessage)
        self._callError(errorMessage)
            
    def _callError(self, errorMessage):
        if self._error != None:
            self._error(errorMessage)
        
    def _callSuccess(self, result):
        if self._success != None:
            self._success(result)

class SyncCall(_CallBase):
    def __init__(self, logger, call, successCall = None, errorCall = None, mutex = None):
        """Creates a synchronous call object
        
        call -- The callable to be called.
                The arguments passed to __call__ will be forwarded to the callable.
        successCall -- If call() does not raise an exception, successCall is called with the result of call().
        errorCall -- If call() raises an exception, errorCall is called with an error message as the only argument.
        mutex -- A QMutex object that will be locked during call().
        """
        super(SyncCall, self).__init__(call, successCall, errorCall, mutex, logger)
        
    def __call__(self, *args, **kwargs):
        self._processCall(args, kwargs)
        
class AsyncCall(QObject, _CallBase):
    _successSig = pyqtSignal(object)
    _errorSig = pyqtSignal(object)
    
    class CallThread(QThread):
        def __init__(self, parent, call):
            QThread.__init__(self, parent)
            self._call = call
    
        def run(self):
            self._call()
    
    def __init__(self, parent, logger, call, successCall = None, errorCall = None, mutex = None):
        """Creates an asynchronous call object
        
        parent -- The parent object for QThread.
        call -- The callable to be called.
                The arguments passed to __call__ will be forwarded to the callable.
        successCall -- If call() does not raise an exception, successCall is called with the result of call().
        errorCall -- If call() raises an exception, errorCall is called with an error message as the only argument.
        mutex -- A QMutex object that will be locked during call().
        """
        QObject.__init__(self, parent)
        _CallBase.__init__(self, call, successCall, errorCall, mutex, logger)
        self._parent = parent

    def _setErrorCall(self, errorCall):
        self._errorSig.connect(errorCall)
        
    def _setSuccessCall(self, successCall):
        self._successSig.connect(successCall)
        
    def _callSuccess(self, result):
        self._successSig.emit(result)
        
    def _callError(self, errorMessage):
        self._errorSig.emit(errorMessage)

    def __call__(self, *args, **kwargs):
        thread = self.CallThread(self._parent, partial(self._processCall, args, kwargs))
        thread.finished.connect(thread.deleteLater)
        thread.start()
