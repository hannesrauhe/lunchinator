from lunchinator.log import getLogger
from functools import wraps

def loggingFunc(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            getLogger().exception(u"Uncaught exception in function")
            raise
    return wrapper
