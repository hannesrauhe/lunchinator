from logging import Handler
from collections import deque

class NotificationLogHandler(Handler):
    def __init__(self):
        super(NotificationLogHandler, self).__init__()
        self._buf = deque(maxlen=100)
    
    def emit(self, record):
        from lunchinator import get_notification_center
        with self.lock:
            self._buf.append(record)
            get_notification_center().emitLogMessage(record)

    def getCachedRecords(self):
        with self.lock:
            return list(self._buf)
        
    def setCacheSize(self, size):
        if self._buf.maxlen != size:
            with self.lock:
                self._buf = deque(self._buf, maxlen=size)