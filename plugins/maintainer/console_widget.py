from PyQt4.QtGui import QVBoxLayout, QTreeView, QStandardItemModel,\
    QStandardItem, QFrame, QHeaderView, QTextEdit, QColor, QItemSelection,\
    QTextOption, QLabel, QSplitter, QWidget
from PyQt4.QtCore import Qt, QVariant
from lunchinator import get_notification_center, convert_string
from lunchinator.log import getCachedLogRecords
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.utilities import formatException
import os, logging, traceback
from StringIO import StringIO
from time import strftime, localtime

class ConsoleWidget(QWidget):
    _RECORD_ROLE = Qt.UserRole + 1
    
    def __init__(self, parent, logger):
        super(ConsoleWidget, self).__init__(parent)
        
        self.logger = logger
        self._errorColor = QVariant(QColor(180, 0, 0))
        self._warningColor = QVariant(QColor(170, 100, 0))
        self._records = []
        
        self._initModel()
        self._initUI()
        
        get_notification_center().connectLogMessage(self._addLogMessage)
        
    def _initUI(self):
        layout = QVBoxLayout(self)
        
        split = QSplitter(Qt.Vertical, self)
        
        layout.setContentsMargins(0, 0, 0, 0)
        
        console = QTreeView(self)
        console.setSortingEnabled(False)
        console.setHeaderHidden(False)
        console.setAlternatingRowColors(True)
        console.setIndentation(0)
        console.setUniformRowHeights(True)
        console.setObjectName(u"__console_log")
        
        console.setFrameShape(QFrame.StyledPanel)
        #if getPlatform() == PLATFORM_MAC:
        #    console.setStyleSheet("QFrame#__console_log{border-width: 1px; border-top-style: none; border-right-style: none; border-bottom-style: solid; border-left-style: none; border-color:palette(mid)}");
        
        console.setModel(self._logModel)
        console.header().setStretchLastSection(False)
        console.header().setResizeMode(3, QHeaderView.Stretch)
        console.selectionModel().selectionChanged.connect(self._selectionChanged)
        split.addWidget(console)
        
        detailsWidget = QWidget(self)
        detailsLayout = QVBoxLayout(detailsWidget)
        detailsLayout.setContentsMargins(0, 0, 0, 0)
        detailsLayout.setSpacing(0)
        
        detailsLayout.addWidget(QLabel(u"Details:", self))
        
        self._detailsView = QTextEdit(self)
        self._detailsView.setReadOnly(True)
        self._detailsView.setWordWrapMode(QTextOption.NoWrap)
        
        detailsLayout.addWidget(self._detailsView, 1)
        
        split.addWidget(detailsWidget)
        
        layout.addWidget(split, 1)
        
    @loggingSlot(QItemSelection, QItemSelection)
    def _selectionChanged(self, newSel, _oldSel):
        if len(newSel.indexes()) == 0:
            self._detailsView.clear()
        else:
            index = newSel.indexes()[0]
            record = self._records[index.row()]
            
            msg = u"%s - In %s:%d: %s" % (strftime("%H:%M:%S", localtime(record.created)),
                                          record.pathname,
                                          record.lineno,
                                          convert_string(record.msg) % record.args)
            if record.exc_info:
                out = StringIO()
                traceback.print_tb(record.exc_info[2], file=out)
                msg += u"\nStack trace:\n" + out.getvalue() + formatException(record.exc_info) + u"\n"
                
            self._detailsView.setPlainText(msg)
        
    def _initModel(self):
        self._logModel = QStandardItemModel(self)
        self._logModel.setColumnCount(5)
        self._logModel.setHorizontalHeaderLabels([u"Time", u"Level", u"Component", u"Message", u"Source"])
        for record in getCachedLogRecords():
            self._addLogMessage(record)
    
    def _createItem(self, text, error, toolTip=None):
        item = QStandardItem()
        item.setEditable(False)
        item.setText(text)
        if error is 1:
            item.setData(self._warningColor, Qt.ForegroundRole)
        elif error is 2:
            item.setData(self._errorColor, Qt.ForegroundRole)
        if toolTip is None:
            toolTip = text
        item.setData(QVariant(toolTip), Qt.ToolTipRole)
        return item
        
    @loggingSlot(object)
    def _addLogMessage(self, record):
        self._records.append(record)
        
        msg = record.msg
        if not isinstance(msg, basestring):
            msg = unicode(msg)
        msg = convert_string(msg) % record.args
        dirname = os.path.dirname(record.pathname)
        source = u"%s:%d" % (os.path.join(os.path.basename(dirname), os.path.basename(record.pathname)), record.lineno)
        fullsource = u"%s:%d" % (record.pathname, record.lineno)
        component = record.name
        if component.startswith("lunchinator."):
            component = component[12:]
        error = 1 if record.levelno == logging.WARNING else 2 if record.levelno == logging.ERROR else 0
        self._logModel.appendRow([self._createItem(strftime("%H:%M:%S", localtime(record.created)), error),
                                  self._createItem(record.levelname, error),
                                  self._createItem(component, error),
                                  self._createItem(msg, error),
                                  self._createItem(source, error, fullsource)])
    
        