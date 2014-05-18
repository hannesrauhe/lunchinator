from lunchinator import log_error, log_debug

def loggingMutex(name, qMutex=False, logging=False):
    if logging:
        return _LoggingMutexQt(name) if qMutex else _LoggingMutexThreading(name)
    elif not qMutex:
        from threading import Lock
        return Lock()
    else:
        from PyQt4.QtCore import QMutex
        return QMutex()

class _LoggingMutex(object):
    def __init__(self, name):
        self.name = name
        self.currentThread = None

    def currentThreadID(self):
        raise NotImplementedError
    
    def enterMutex(self):
        raise NotImplementedError
    
    def exitMutex(self, *_args, **_kwargs):
        raise NotImplementedError

    def acquire(self):
        raise NotImplementedError
    
    def release(self):
        raise NotImplementedError

    def __enter__(self):
        if self.currentThreadID() == self.currentThread:
            import traceback
#             log_error("Requesting lock from the same thread")
#             traceback.print_stack()
            raise Exception("Requesting lock from the same thread")
        
        log_debug("Requesting mutex", self.name)
        self.enterMutex()
        self.currentThread = self.currentThreadID()
        log_debug("Entering mutex", self.name)
        return self
    
    def __exit__(self, *args, **kwargs):
        log_debug("Leaving mutex", self.name)
        self.currentThread = None
        self.exitMutex(*args, **kwargs)
        
class _LoggingMutexThreading(_LoggingMutex):
    def __init__(self, name):
        super(_LoggingMutexThreading, self).__init__(name)
        from threading import Lock
        self.mutex = Lock()

    def currentThreadID(self):
        from threading import currentThread
        return currentThread().ident

    def acquire(self):
        self.mutex.acquire()
        
    def release(self):
        self.mutex.release()

    def enterMutex(self):
        self.mutex.__enter__()
    
    def exitMutex(self, *args, **kwargs):
        self.mutex.__exit__(*args, **kwargs)
        
class _LoggingMutexQt(_LoggingMutex):
    def __init__(self, name):
        super(_LoggingMutexQt, self).__init__(name)
        from PyQt4.QtCore import QMutex
        self.mutex = QMutex()

    def currentThreadID(self):
        from PyQt4.QtCore import QThread
        return QThread.currentThreadId()
    
    def acquire(self):
        self.mutex.lock()
        
    def release(self):
        self.mutex.unlock()
    
    def enterMutex(self):
        self.mutex.lock()
        
    def exitMutex(self, *_args, **_kwargs):
        self.mutex.unlock()
