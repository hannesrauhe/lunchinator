from logging import Handler

class NotificationLogHandler(Handler):
    def emit(self, record):
        from lunchinator import get_notification_center
        get_notification_center().emitLogMessage(record)
