from logging import Handler

class ErrorNotificationHandler(Handler):
    def emit(self, record):
        print record
