from lunchinator.log import getLogger
from PyQt4.QtCore import pyqtSlot
from functools import wraps
import types

def loggingSlot(*args, **kwargs):
    if len(args) == 0 or isinstance(args[0], types.FunctionType):
        args = []
    def slotdecorator(func):
        @pyqtSlot(*args, **kwargs)
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except:
                getLogger().exception(u"Uncaught exception in PyQT slot")
        return wrapper

    return slotdecorator
