import unittest, Queue
from lunchinator import get_notification_center, get_peers, get_settings, get_server

class notificationCenterTestCase(unittest.TestCase):
    def setUp(self):
        self.testResult = Queue.Queue()
        
    def tearDown(self):
        if get_server().has_gui():
            get_notification_center().processSignalsNow()
        assert "Success" == self.testResult.get(timeout=10)
            
    def setTestResult(self, result):
        self.testResult.put(result)
        
    def testMemberRemovalLock(self):
        get_notification_center().connectMemberRemoved(self.connect_testMemberRemovalLock)
        
        print "Removing myself as Member"
        mIPs=get_peers().getPeerIPs(get_settings().get_ID())
        print "Using IPs:",mIPs
        get_peers().removeMembersByIP(mIPs)
    
    def connect_testMemberRemovalLock(self, peerID):
        print "Removed",peerID,"; IPs of this ID:"
        print get_peers().getPeerIPs(pID=peerID)
        
        get_notification_center().disconnectMemberRemoved(self.connect_testMemberRemovalLock)
        self.setTestResult("Success")
        
    def testDBSettingChanged(self):
        get_notification_center().connectDBSettingChanged(self.connect_testDBSettingChanged)
        #todo(Hannes) test the real deal, not only emitting
        get_notification_center().emitDBSettingChanged("UnitTestConn")
        
    def connect_testDBSettingChanged(self,connName):
        get_notification_center().disconnectDBSettingChanged(self.connect_testDBSettingChanged)
        if connName == "UnitTestConn":
            self.setTestResult("Success")        
        else:
            self.setTestResult("%s changed, expected UnitTestconn"%connName) 