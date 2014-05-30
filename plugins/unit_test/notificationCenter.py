import unittest
from lunchinator import get_notification_center, get_peers, get_settings

class notificationCenterTestCase(unittest.TestCase):         
    def testMemberRemovalLock(self):
        get_notification_center().connectMemberRemoved(self.connect_test_lock)
        print "Removing myself as Member"
        mIPs=get_peers().getPeerIPs(get_settings().get_ID())
        print "Using IPs:",mIPs
        get_peers().removeMembersByIP(mIPs)
    
    def connect_test_lock(self, peerID):
        print "Removed",peerID,"; IPs of this ID:"
        print get_peers().getPeerIPs(pID=peerID)
        