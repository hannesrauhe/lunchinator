from lunchinator.table_models import TableModelBase
from lunchinator import get_peers, log_debug
from lunchinator.utilities import getTimeDifference
from lunchinator.lunch_settings import lunch_settings
import time
from functools import partial
from datetime import datetime
from PyQt4.QtCore import Qt, QVariant, QModelIndex, QTimer
from PyQt4.QtGui import QColor

class MembersTableModel(TableModelBase):
    LUNCH_TIME_TIMER_ROLE = TableModelBase.SORT_ROLE + 1
    _NAME_KEY = u'name'
    _GROUP_KEY = u"group"
    _LUNCH_BEGIN_KEY = u"next_lunch_begin"
    _LUNCH_END_KEY = u"next_lunch_end"
    
    NAME_COL_INDEX = 0
    GROUP_COL_INDEX = 1
    LUNCH_TIME_COL_INDEX = 2
    SEND_TO_COL_INDEX = 3
    
    def __init__(self, dataSource):
        columns = [(u"Name", self._updateNameItem),
                   (u"Group", self._updateGroupItem),
                   (u"LunchTime", self._updateLunchTimeItem)]
        super(MembersTableModel, self).__init__(dataSource, columns)
        
        # Called before server is running, no need to lock here
        for peerID in self.dataSource:
            infoDict = dataSource.getPeerInfo(peerID)
            self.appendContentRow(peerID, infoDict)
            
    def _getRowToolTip(self, peerID, _infoDict):
        return u"ID: %s\nIPs: %s" % (peerID, ', '.join(get_peers().getPeerIPs(peerID)))

    def _updateIpItem(self, ip, _, item):
        item.setData(QVariant(ip), Qt.DisplayRole)

    def _updateNameItem(self, ip, infoDict, item):
        if self._NAME_KEY in infoDict:
            item.setText(infoDict[self._NAME_KEY])
        else:
            item.setText(ip)
        
    def removeRow(self, row, parent=QModelIndex()):
        # ensure no timer is active after a row has been removed
        item = self.item(row, self.LUNCH_TIME_COL_INDEX)
        timer = item.data(self.LUNCH_TIME_TIMER_ROLE)
        if timer != None:
            timer.stop()
            timer.deleteLater()
        return TableModelBase.removeRow(self, row, parent)
        
    def _updateLunchTimeItem(self, ip, infoDict, item):
        oldTimer = item.data(self.LUNCH_TIME_TIMER_ROLE)
        if oldTimer != None:
            oldTimer.stop()
            oldTimer.deleteLater()
        if self._LUNCH_BEGIN_KEY in infoDict and self._LUNCH_END_KEY in infoDict:
            item.setText(infoDict[self._LUNCH_BEGIN_KEY]+"-"+infoDict[self._LUNCH_END_KEY])
            try:
                beginTime = datetime.strptime(infoDict[self._LUNCH_BEGIN_KEY], lunch_settings.LUNCH_TIME_FORMAT)
                beginTime = beginTime.replace(year=2000)
                item.setData(QVariant(time.mktime(beginTime.timetuple())), self.SORT_ROLE)
                timeDifference = getTimeDifference(infoDict[self._LUNCH_BEGIN_KEY],infoDict[self._LUNCH_END_KEY])
                if timeDifference != None:
                    if timeDifference > 0:
                        item.setData(QColor(0, 255, 0), Qt.DecorationRole)
                    else:
                        item.setData(QColor(255, 0, 0), Qt.DecorationRole)
                    
                    if timeDifference != 0:
                        timer = QTimer(item.model())
                        timer.timeout.connect(partial(self._updateLunchTimeItem, ip, infoDict, item))
                        timer.setSingleShot(True)
                        timer.start(abs(timeDifference))
            except ValueError:
                log_debug("Ignoring illegal lunch time:", infoDict[self._LUNCH_BEGIN_KEY])
        else:
            item.setData(QVariant(-1), self.SORT_ROLE)
            
    def _updateGroupItem(self, _peerID, infoDict, item):
        if self._GROUP_KEY in infoDict:
            item.setText(infoDict[self._GROUP_KEY])
        else:
            item.setText(u"")
        
    def _updateLastSeenItem(self, peerID, _, item):
        intValue = -1
        timeout = self.dataSource.getIDLastSeen(peerID)
        if timeout != None:
            intValue = int(time.time() - timeout)
        item.setData(QVariant(intValue), Qt.DisplayRole)
    