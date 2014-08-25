from PyQt4.QtGui import QVBoxLayout, QDialog, QDialogButtonBox, QLabel,\
    QTextOption, QColor, QCheckBox, QTextEdit, QWidget, QHBoxLayout, QFrame
from PyQt4.QtCore import Qt, QSize
from lunchinator import get_notification_center, convert_string
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.utilities import formatException, getPlatform, PLATFORM_MAC

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
        layout.setSpacing(0)
        
        labelLayout = QHBoxLayout()
        labelLayout.addWidget(QLabel(u"Sorry, something went wrong:", self))
        labelLayout.setContentsMargins(10, 0, 0, 0)
        layout.addLayout(labelLayout)
        layout.addSpacing(5)
        self._errorLog = QTextEdit(self)
        self._errorLog.setReadOnly(True)
        self._errorLog.setWordWrapMode(QTextOption.NoWrap)
        self._errorLog.setTextColor(QColor(180, 0, 0))
        self._errorLog.setObjectName(u"__ERROR_LOG_")
        
        self._errorLog.setFrameShape(QFrame.StyledPanel)
        if getPlatform() == PLATFORM_MAC:
            self._errorLog.setStyleSheet("QFrame#__ERROR_LOG_{border-width: 1px; border-top-style: solid; border-right-style: none; border-bottom-style: solid; border-left-style: none; border-color:palette(mid)}");
            
        layout.addWidget(self._errorLog)
        
        bottomWidget = QWidget(self)
        bottomLayout = QHBoxLayout(bottomWidget)
        
        self._notAgain = QCheckBox(u"Please, no more error messages!", self)
        bottomLayout.addWidget(self._notAgain, 1, Qt.AlignTop)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        buttonBox.rejected.connect(self.reject)
        bottomLayout.addWidget(buttonBox)
        
        layout.addWidget(bottomWidget)
        
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
            if record.levelno >= logging.ERROR:
                recMsg = record.msg
                if not isinstance(recMsg, basestring):
                    recMsg = unicode(recMsg)
                err = convert_string(recMsg) % record.args
                component = record.name
                if component.startswith("lunchinator."):
                    component = component[12:]
                    
                msg = u"%s - In component %s (%s:%d):\n%s" % (strftime("%H:%M:%S", localtime(record.created)),
                                                              component,
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
            from lunchinator.log import getCoreLogger
            getCoreLogger().info(formatException())
            
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import sys
    from lunchinator.log import initializeLogger, getCoreLogger

    initializeLogger()
    app = QApplication(sys.argv)
    window = ErrorLogDialog(None)
    getCoreLogger().error(u"Foo error")
    try:
        raise ValueError("foo")
    except:
        getCoreLogger().exception("An exception occurred")
    
    app.exec_()

