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
        if self.currentThreadID() == self.currentThread:
            raise Exception("Requesting lock from the same thread")
        
        self._acquire()
        self.currentThread = self.currentThreadID()
    
    def _acquire(self):
        raise NotImplementedError
    
    def release(self):
        self.currentThread = None
        self._release()
    
    def _release(self):
        raise NotImplementedError

    def __enter__(self):
        if self.currentThreadID() == self.currentThread:
            raise Exception("Requesting lock from the same thread")
        
        self.enterMutex()
        self.currentThread = self.currentThreadID()
        return self
    
    def __exit__(self, *args, **kwargs):
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

    def _acquire(self):
        self.mutex.acquire()
        
    def _release(self):
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
    
    def _acquire(self):
        self.mutex.lock()
        
    def _release(self):
        self.mutex.unlock()
    
    def enterMutex(self):
        self.mutex.lock()
        
    def exitMutex(self, *_args, **_kwargs):
        self.mutex.unlock()
