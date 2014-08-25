from logging_level_settings.combobox_delegate import ComboboxDelegate
from lunchinator import convert_string, get_notification_center
from lunchinator.log.logging_slot import loggingSlot
from lunchinator.log import getLoggerNames
from lunchinator.table_models import TableModelBase
from lunchinator.log.lunch_logger import getSpecificLoggingLevel,\
    getLoggingLevel
    
from PyQt4.QtGui import QWidget, QVBoxLayout, QTreeView,\
    QSortFilterProxyModel, QHBoxLayout, QLabel, QComboBox, QHeaderView
from PyQt4.QtCore import Qt
import logging
from functools import partial

class LogLevelModel(TableModelBase):
    NAME_COLUMN = 0
    LEVEL_COLUMN = 1
    
    _LEVEL_TEXT = {None : u"Default",
                   logging.DEBUG : u"Debug",
                   logging.INFO : u"Info",
                   logging.WARNING: u"Warning",
                   logging.ERROR: u"Error",
                   logging.CRITICAL : u"Critical"}
    
    def __init__(self, logger):
        columns = [(u"Component", self._updateComponentItem),
                   (u"Level", self._updateLevelItem)]
        super(LogLevelModel, self).__init__(None, columns, logger)
        
        for l in getLoggerNames():
            self.externalRowAppended(l, None)
            
    def _updateComponentItem(self, l, _data, item):
        if l.startswith(u"lunchinator."):
            n = l[12:]
        else:
            n = l
        item.setText(n)
        
    def _updateLevelItem(self, l, _data, item):
        level = getSpecificLoggingLevel(l)
        item.setEditable(True)
        item.setText(self._LEVEL_TEXT[level])
            
class LogLevelTable(QTreeView):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.column() == LogLevelModel.LEVEL_COLUMN:
                self.stopEditing()
                self.edit(index)
                event.accept()
                return
            else:
                self.stopEditing()
        super(LogLevelTable, self).mousePressEvent(event)
        
    def stopEditing(self):
        if self.itemDelegate().getEditor() != None:
            self.closeEditor(self.itemDelegate().getEditor(), ComboboxDelegate.NoHint)
            self.itemDelegate().editorClosing(self.itemDelegate().getEditor(), ComboboxDelegate.NoHint)
    
    def mouseMoveEvent(self, event):
        event.ignore()
    
class LoggingLevelGUI(QWidget):
    def __init__(self, logger, parent):
        super(LoggingLevelGUI, self).__init__(parent)
        self.logger = logger
        self._initUI()
        self._initModel()
        
        self._logTable.setModel(self._sortFilterModel)
        self._logTable.sortByColumn(LogLevelModel.NAME_COLUMN, Qt.AscendingOrder)
        
        self._logTable.header().setStretchLastSection(False)
        self._logTable.header().setResizeMode(LogLevelModel.NAME_COLUMN, QHeaderView.Stretch)
        
        get_notification_center().connectLoggerAdded(partial(self._logModel.externalRowAppended, data=None))
        get_notification_center().connectLoggerAdded(self._logModel.externalRowRemoved)
        get_notification_center().connectLoggingLevelChanged(self._loggingLevelChanged)
        
    def _initUI(self):
        layout = QVBoxLayout(self)
        
        globalLevelWidget = QWidget(self)
        glLayout = QHBoxLayout(globalLevelWidget)
        glLayout.setContentsMargins(0, 0, 0, 0)
        glLayout.addWidget(QLabel(u"Default Logging Level:", globalLevelWidget))
        
        self._globalLevelCombo = QComboBox()
        self._globalLevelCombo.addItems([u"Debug",
                                         u"Info",
                                         u"Warning",
                                         u"Error",
                                         u"Critical"])
        globalLevel = getLoggingLevel(None)
        self._setGlobalLevel(globalLevel)
        glLayout.addWidget(self._globalLevelCombo, 1, Qt.AlignLeft)
        
        layout.addWidget(globalLevelWidget)
        
        self._logTable = LogLevelTable(self) 
        self._logTable.setIndentation(0)
        self._logTable.setItemDelegate(ComboboxDelegate(LogLevelModel.LEVEL_COLUMN, self))
        self._logTable.setFocusPolicy(Qt.NoFocus)
        self._logTable.setSortingEnabled(True)
        self._logTable.setSelectionMode(QTreeView.NoSelection)
        self._logTable.setVerticalScrollMode(LogLevelTable.ScrollPerPixel)
        layout.addWidget(self._logTable)

    def _initModel(self):                
        self._logModel = LogLevelModel(self.logger)
        
        self._sortFilterModel = QSortFilterProxyModel(self)
        self._sortFilterModel.setSourceModel(self._logModel)
        self._sortFilterModel.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._sortFilterModel.setSortRole(Qt.DisplayRole)
        self._sortFilterModel.setDynamicSortFilter(True)
        
    def _setGlobalLevel(self, globalLevel):
        globalLevelText = LogLevelModel._LEVEL_TEXT[globalLevel]
        self._globalLevelCombo.setCurrentIndex(self._globalLevelCombo.findText(globalLevelText, flags=Qt.MatchExactly))
        
    def getGlobalLevelText(self):
        return convert_string(self._globalLevelCombo.currentText())
        
    @loggingSlot(object, object)
    def _loggingLevelChanged(self, loggerName, newLevel):
        # connected to notification center
        if loggerName is None:
            self._setGlobalLevel(newLevel)
        else:
            self._logModel.externalRowUpdated(loggerName, None)
        
    def resizeColumns(self):
        self._logTable.resizeColumnToContents(LogLevelModel.NAME_COLUMN)
    
    def getModel(self):
        return self._logModel
    
    def getTable(self):
        return self._logTable
    
    def reset(self):
        self._logModel.updateTable()
        self._setGlobalLevel(getLoggingLevel(None))
    