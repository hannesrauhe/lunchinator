import time, math
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QGridLayout, QLabel, QSpinBox, QLineEdit
from lunchinator.log.logging_slot import loggingSlot
from lunchinator import convert_string

class statTimelineTab(QtGui.QWidget):
    def __init__(self, parent, connPlugin, logger):
        super(statTimelineTab, self).__init__(parent)
        lay = QGridLayout(self)
        vw = statTimelineWidget(parent, connPlugin, logger)
        lay.addWidget(vw, 0, 0, 1, 2)
        lay.addWidget(QLabel("Scale:"), 1, 0, Qt.AlignRight)
        spinbox = QSpinBox(self)
        spinbox.setValue(vw.getScale())
        spinbox.valueChanged.connect(vw.setScale)
        lay.addWidget(spinbox, 1, 1)
    
class statTimelineWidget(QtGui.QWidget):    
    def __init__(self, parent, connPlugin, logger):
        super(statTimelineWidget, self).__init__(parent)
        self.logger = logger
        self._connPlugin = connPlugin
        self.scale = 1

    @loggingSlot(int)
    def setScale(self, i):
        self.scale = i
        self.update()
        
    def getScale(self):
        return self.scale

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawPoints(qp)
        except:
            self.logger.exception("Error painting")
        qp.end()
        
    def drawPoints(self, qp):      
        qp.setPen(QtCore.Qt.black)
        size = self.size()
        
        maxTime = time.time()
        minTime = int(maxTime - size.width() * self.scale)
        try:
            tmp = self._connPlugin.query("SELECT mtype, count(*) FROM statistics_messages " + \
                                        "WHERE rtime between %d and %d GROUP BY mtype" % (minTime, maxTime))
        except:
            # database error, probably table does not exist
            tmp = []
        
        numYAreas = len(tmp)
        if 0 == numYAreas:
            return
        mtypes = {}
        yAreaSize = size.height() / numYAreas
        yAreaPos = [0] * numYAreas
        for i, t in enumerate(tmp):
            mtypes[t[0]] = i
            yAreaPos[i] = int((i * yAreaSize) + (size.height() / numYAreas / 2))
            qp.drawText(10, yAreaPos[i], "%s (%d)" % (t[0], t[1]))
        
        for pos, val in zip(range(size.width(), 60, -60), range(0, size.width(), 60)):
            h_val = 0
            min_val = self.scale * val / 60
            if min_val >= 60:
                h_val = min_val // 60
                min_val = min_val % 60
            qp.drawText(pos, 10, "%d:%02d" % (h_val, min_val))
            
        
        qp.setPen(QtCore.Qt.red)
        timelineData = self._connPlugin.query("SELECT mtype, sender, rtime " + \
                                            "FROM statistics_messages " + \
                                            "WHERE rtime between %d and %d" % (minTime, maxTime))

        lastx = -1
        xcounter = 0
        for mtype, sender, rtime in timelineData:
            x = int((rtime - minTime) / self.scale)
            xcounter = xcounter + 1 if lastx == x and xcounter < yAreaSize else 0
            lastx = x
            y = yAreaPos[mtypes[mtype]] + xcounter
            qp.drawPoint(x, y)   
#             print x,y,mtype

class statSwarmTab(QtGui.QWidget):
    def __init__(self, parent, connPlugin, logger):
        super(statSwarmTab, self).__init__(parent)
        lay = QGridLayout(self)
        vw = statSwarmWidget(parent, connPlugin, logger)
        lay.addWidget(vw, 0, 0, 0, 4)
        lay.addWidget(QLabel("Period:"), 1, 0, Qt.AlignRight)
        spinbox = QSpinBox(self)
        spinbox.setValue(vw.getPeriod())
        spinbox.valueChanged.connect(vw.setPeriod)
        lay.addWidget(spinbox, 1, 1)
    
        lay.addWidget(QLabel("mType Filter:"), 1, 2, Qt.AlignRight)
        tBox = QLineEdit(self)
        tBox.setText(vw.getmType())
        tBox.textChanged.connect(vw.setmType)
        lay.addWidget(tBox, 1, 3)
    
class statSwarmWidget(QtGui.QWidget):    
    def __init__(self, parent, connPlugin, logger):
        super(statSwarmWidget, self).__init__(parent)
        self.logger = logger
        self._connPlugin = connPlugin
        self.period = 1
        self.mtype = "HELO%"
        
        self.last_painted_period = 0
        self.last_painted_mtype = ""
        
        #const:
        self.maxCircleSize = 50
        self.myCircleSize = 20        
        self.query_unbuffer = time.time()
        
        
    @loggingSlot(int)
    def setPeriod(self, i):
        self.period = i
        self.update()
        
    def getPeriod(self):
        return self.period
    
    @loggingSlot(QString)
    def setmType(self, i):
        self.mtype = convert_string(i)
        self.update()
        
    def getmType(self):
        return self.mtype
    
    def retrieveDataFromDatabase(self):
        if time.time()<self.query_unbuffer and \
          self.last_painted_mtype == self.mtype and \
          self.last_painted_period == self.period:
            return
        
        self.last_painted_period = self.period
        self.last_painted_mtype = self.mtype
                
        self.scale = 1
        self.numPeers = 0
        self.peerNodes = {}
        
        maxTime = time.time()
        minTime = maxTime - self.period*60*60
        
        try:
            tmp = self._connPlugin.query("SELECT sender, count(*) FROM statistics_messages " + \
                                        "WHERE rtime between ? and ? "+ \
                                        "AND mType LIKE ?"
                                        "GROUP BY sender", minTime, maxTime, str(self.mtype))
        except:
            # database error, probably table does not exist
            tmp = []
        self.query_unbuffer = time.time()+5
        self.numPeers = len(tmp)
        if 0 == self.numPeers :
            return
        
        for sender, count in tmp:
            while count/self.scale > self.maxCircleSize:
                self.scale += 1
            self.peerNodes[sender] = count

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawPoints(qp)
        qp.end()
        
    def drawPoints(self, qp):      
        qp.setPen(QtCore.Qt.black)
        
        size = self.size()
        
        centerX = size.width() / 2
        centerY = size.height() / 2
        qp.drawEllipse(centerX - self.myCircleSize/2, centerY - self.myCircleSize/2, self.myCircleSize, self.myCircleSize)
                    
        self.retrieveDataFromDatabase()
        if 0 == self.numPeers :
            return
        
        qp.drawText(10,10,"%d"%self.scale)
        i = 0
        for sender, count in self.peerNodes.iteritems():
            distanceX = size.width() / 4
            distanceY = size.height() / 4
            circleSize = count/self.scale
            t = i * (2 * math.pi / self.numPeers)
            x = distanceX * math.cos(t) + centerX - circleSize/2;
            y = distanceY * math.sin(t) + centerY - circleSize/2;
            qp.drawEllipse(x, y, circleSize, circleSize)
            qp.drawText(x, y - 5, sender)
            i += 1
