from PyQt4.QtCore import pyqtSlot
from functools import wraps
import types, inspect

def loggingSlot(*args, **kwargs):
    if len(args) == 0 or isinstance(args[0], types.FunctionType):
        args = []
    def slotdecorator(func):
        from lunchinator.log import getCoreLogger
        fArgs, _fVarargs, _fKeywords, _fDefaults = inspect.getargspec(func)
        maxNumArgs = len(fArgs)
                
        @pyqtSlot(*args, **kwargs)
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*(args[:maxNumArgs - len(kwargs)]), **kwargs)
            except:
                if len(args) > 0 and hasattr(args[0], "logger"):
                    logger = args[0].logger
                else:
                    logger = getCoreLogger()
                logger.exception(u"Uncaught exception in PyQT slot")
        return wrapper

    return slotdecorator
