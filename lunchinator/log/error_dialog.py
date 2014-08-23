from PyQt4.QtGui import QVBoxLayout, QDialog, QDialogButtonBox, QLabel,\
    QTextOption, QColor, QCheckBox, QTextEdit
from PyQt4.QtCore import Qt, QSize
from lunchinator import get_notification_center, convert_string
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.utilities import formatException

import logging, traceback
from StringIO import StringIO
from time import localtime, strftime
from lunchinator.log.lunch_logger import getCachedLogRecords

class ErrorLogDialog(QDialog):
    def __init__(self, parent):
        super(ErrorLogDialog, self).__init__(parent, Qt.WindowStaysOnTopHint)
        self._empty = True
        
        self._initUI()
        self.setWindowTitle("Error")
        get_notification_center().connectLogMessage(self._checkLogMessage)
        
        for record in getCachedLogRecords():
            self._checkLogMessage(record)
        
    def sizeHint(self):
        return QSize(400, 200)
        
    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(QLabel(u"Sorry, something went wrong:", self))
        self._errorLog = QTextEdit(self)
        self._errorLog.setReadOnly(True)
        self._errorLog.setWordWrapMode(QTextOption.NoWrap)
        self._errorLog.setTextColor(QColor(180, 0, 0))
        layout.addWidget(self._errorLog)
        
        self._notAgain = QCheckBox(u"Please, no more error messages!", self)
        layout.addWidget(self._notAgain)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)
        
    @loggingSlot()
    def reject(self):
        self._errorLog.clear()
        self._empty = True
        return QDialog.reject(self)
    
    @loggingSlot(object)
    def _checkLogMessage(self, record):
        try:
            if self._notAgain.checkState() == Qt.Checked:
                return
            if record.levelno == logging.ERROR:
                recMsg = record.msg
                if not isinstance(recMsg, basestring):
                    recMsg = unicode(recMsg)
                err = convert_string(recMsg) % record.args
                msg = u"%s - In %s:%d: %s" % (strftime("%H:%M:%S", localtime(record.created)),
                                              record.pathname,
                                              record.lineno,
                                              err)
                if record.exc_info:
                    out = StringIO()
                    traceback.print_tb(record.exc_info[2], file=out)
                    msg += u"\nStack trace:\n" + out.getvalue() + formatException(record.exc_info) + u"\n"
                    
                self._errorLog.append(msg)
                self._empty = False
                if not self.isVisible():
                    self.showNormal()
                    self.raise_()
                    self.activateWindow()
        except:
            getLogger().info(formatException())
            
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys
    from lunchinator.log import getLogger, initializeLogger

    initializeLogger()
    app = QApplication(sys.argv)
    window = ErrorLogDialog(None)
    getLogger().error(u"Foo error")
    try:
        raise ValueError("foo")
    except:
        getLogger().exception("An exception occurred")
    
    app.exec_()

