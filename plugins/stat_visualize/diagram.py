import sys, random, time
from PyQt4 import QtGui, QtCore

class statTimelineWidget(QtGui.QWidget):
    
    def __init__(self, connPlugin):
        super(statTimelineWidget, self).__init__()
        self.connPlugin = connPlugin
        self.scale = 1
        '''
        self.initUI()
        
    def initUI(self):      

        self.setGeometry(300, 300, 280, 170)
        self.setWindowTitle('Points')
        self.show()'''
        
    def setScale(self, i):
        self.scale = i
        self.update()
        
    def getScale(self):
        return self.scale

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawPoints(qp)
        qp.end()
        
    def drawPoints(self, qp):      
        qp.setPen(QtCore.Qt.black)
        size = self.size()
        
        maxTime = time.time()
        minTime = int(maxTime - size.width() * self.scale)
        tmp = self.connPlugin.query("SELECT mtype, count(*) FROM messages GROUP BY mtype")
        numYAreas = len(tmp)
        mtypes = {}
        yAreaPos = [0] * numYAreas
        for i, t in enumerate(tmp):
            mtypes[t[0]] = i
            yAreaPos[i] = int((i * size.height() / numYAreas) + (size.height() / numYAreas / 2))
            qp.drawText(10, yAreaPos[i], "%s (%d)" % (t[0], t[1]))
        
        for pos, val in zip(range(size.width(), 100, -100), range(0, size.width(), 100)):
            qp.drawText(pos, 10, "%d" % int(self.scale * val))
            
        
        qp.setPen(QtCore.Qt.red)
        timelineData = self.connPlugin.query("SELECT mtype, sender, rtime " + \
                                            "FROM messages " + \
                                            "WHERE rtime between %d and %d" % (minTime, maxTime))
        zeroPoint = maxTime - size.width()
        for mtype, sender, rtime in timelineData:
            x = int((rtime - minTime) / self.scale)
            y = yAreaPos[mtypes[mtype]]
            qp.drawPoint(x, y)   
#             print x,y,mtype
