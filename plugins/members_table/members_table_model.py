from lunchinator.table_models import TableModelBase
from lunchinator import get_peers
from lunchinator.log import getLogger
from lunchinator.utilities import getTimeDifference
from lunchinator.lunch_settings import lunch_settings
import time
from datetime import datetime
from PyQt4.QtCore import Qt, QVariant
from PyQt4.QtGui import QColor, QBrush

class MembersTableModel(TableModelBase):
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
        
        self._grayBrush = QBrush(QColor(150,150,150))
        self._blackBrush = QBrush(QColor(0,0,0))
        
        self._green = QColor(0, 255, 0)
        self._grayGreen = QColor(150,220,150)
        
        self._red = QColor(255, 0, 0)
        self._grayRed = QColor(200,150,150)
        
        # Called before server is running, no need to lock here
        for peerID in self.dataSource:
            infoDict = dataSource.getPeerInfo(peerID)
            self.appendContentRow(peerID, infoDict)
            
    def _getRowToolTip(self, peerID, _infoDict):
        return u"ID: %s\nIPs: %s" % (peerID, ', '.join(get_peers().getPeerIPs(pID=peerID)))

    def _grayOutIfNoMember(self, item, peerID):
        if not self.dataSource.isMember(pID=peerID):
            item.setData(self._grayBrush, Qt.ForegroundRole)
        else:
            item.setData(self._blackBrush, Qt.ForegroundRole)

    def _updateNameItem(self, peerID, _infoDict, item):
        item.setText(get_peers().getDisplayedPeerName(pID=peerID))
        self._grayOutIfNoMember(item, peerID)
        
    def _updateLunchTimeItem(self, peerID, infoDict, item):
        isMember = self.dataSource.isMember(pID=peerID)
        if self._LUNCH_BEGIN_KEY in infoDict and self._LUNCH_END_KEY in infoDict:
            item.setText(infoDict[self._LUNCH_BEGIN_KEY]+"-"+infoDict[self._LUNCH_END_KEY])
            try:
                beginTime = datetime.strptime(infoDict[self._LUNCH_BEGIN_KEY], lunch_settings.LUNCH_TIME_FORMAT)
                beginTime = beginTime.replace(year=2000)
                item.setData(QVariant(time.mktime(beginTime.timetuple())), self.SORT_ROLE)
                timeDifference = getTimeDifference(infoDict[self._LUNCH_BEGIN_KEY],infoDict[self._LUNCH_END_KEY])
                if timeDifference != None:
                    if timeDifference > 0:
                        item.setData(self._green if isMember else self._grayGreen, Qt.DecorationRole)
                    else:
                        item.setData(self._red if isMember else self._grayRed, Qt.DecorationRole)
            except ValueError:
                getLogger().debug("Ignoring illegal lunch time: %s", infoDict[self._LUNCH_BEGIN_KEY])
        else:
            item.setData(QVariant(-1), self.SORT_ROLE)
            
        self._grayOutIfNoMember(item, peerID)
            
    def _updateGroupItem(self, peerID, infoDict, item):
        if self._GROUP_KEY in infoDict:
            item.setText(infoDict[self._GROUP_KEY])
        else:
            item.setText(u"")
        self._grayOutIfNoMember(item, peerID)
        
    def _dataForKey(self, key):
        return self.dataSource.getPeerInfo(pID=key)
        
    def updateLunchTimeColumn(self):
        self.updateColumn(self.LUNCH_TIME_COL_INDEX)
        