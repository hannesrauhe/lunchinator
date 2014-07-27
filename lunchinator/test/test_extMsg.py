'''
Created on 25.07.2014

@author: Hannes Rauhe
'''
import unittest, random, string
from lunchinator.lunch_socket import *

class extMsgTest(unittest.TestCase):
    def setUp(self):
        self.split_size = 512

    def tearDown(self):
        pass
    
    def string_generator(self, size=6, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))
    
    def testOutgoingBasic(self):        
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str
        
        eMsg = extMessageOutgoing(self.test_str, self.split_size)
        self.assertEqual(self.test_str, eMsg.getPlainMessage())
        for f in eMsg.getFragments():
            self.assertTrue(f.startswith("HELOX"))
            
    def testOutInPipeline(self):        
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        eMsgIn = extMessageIncoming()
        for f in eMsgOut.getFragments():
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
        self.assertRaises(Exception, eMsgIn.addFragment, "fdjaf")
        
    def testHash(self):
        self.test_str = self.string_generator(690).encode('utf-8')
        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        self.assertEqual(len(eMsgOut.hashPlainMessage()), 4)
        
    def testNoSplit(self):
        self.test_str = self.string_generator(500).encode('utf-8')
        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        eMsgIn = extMessageIncoming()
        eMsgIn.addFragment(eMsgOut.getFragments()[0])
        
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()