from functools import wraps

def loggingFunc(func):
    from lunchinator.log import getCoreLogger
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            if len(args) > 0 and hasattr(args[0], "logger"):
                logger = args[0].logger
            else:
                logger = getCoreLogger()
            logger.exception(u"Uncaught exception in function")
            raise
    return wrapper
