'''
Created on 25.07.2014

@author: Hannes Rauhe
'''
import unittest, random, string
from lunchinator.lunch_socket import *
from lunchinator.log import initializeLogger, getCoreLogger

class extMsgTest(unittest.TestCase):
    test_key = "3CDC 2903 4198 CA7A FB18 5EB3 8F7A 8017 17F5 7DC2".replace(" ", "") #"0x17F57DC2"
    
    def setUp(self):
        self.split_size = 512
        try:
            getCoreLogger()
        except:
            initializeLogger()

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
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
        self.assertRaises(Exception, eMsgIn.addFragment, "fdjaf")
        
    def testMerge(self):        
        self.test_str = self.string_generator(2690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            other = extMessageIncoming(f)
            eMsgIn.merge(other)
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        #message should not be signed nor encrypted
        self.assertFalse(eMsgIn.isEncrypted(), "Message status byte says encrpyted; shouldn't be")
        self.assertFalse(eMsgIn.isSigned(), "Message status byte says signed; shouldn't be")
        self.assertTrue(eMsgIn.isCompressed(), "Message status byte says not compressed; should be")
        
        self.assertRaises(Exception, eMsgIn.addFragment, "fdjaf")
        
    def testHash(self):
        self.test_str = self.string_generator(690).encode('utf-8')
        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        self.assertEqual(len(eMsgOut.hashPlainMessage()), 4)
        
    def testNoSplit(self):
        self.test_str = self.string_generator(self.split_size-1).encode('utf-8')
        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        frag = eMsgOut.getFragments()
        self.assertEqual(len(frag), 1, "Plain texts that would fit into one message do not\
                     fit into one extended message fragment anymore -> Header is too large")
        
        eMsgIn = extMessageIncoming(frag[0])
        
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
    
    '''test (force) disabled compression'''
    def testNoCompression(self):
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size, compress=None)
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertFalse(eMsgIn.isCompressed(), "Status byte says compressed")
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
    def testUnicode(self):
        self.test_str = self.string_generator(self.split_size-100, string.printable).encode('utf-8')
        eMsgOut = extMessageOutgoing(self.test_str, self.split_size)
        frag = eMsgOut.getFragments()
        
        eMsgIn = extMessageIncoming(frag[0])
        
        self.assertTrue(eMsgIn.isComplete())
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())

    def testEncryption(self):
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size, encrypt_key=self.test_key)
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertTrue(eMsgIn.isEncrypted(), "Status byte says not encrypted")
        self.assertFalse(eMsgIn.isSigned(), "Status byte says signed")
        self.assertEqual(eMsgIn.getSignatureInfo()['fingerprint'], None)
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
    def testSign(self):
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size, sign_key=self.test_key)
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertTrue(eMsgIn.isSigned(), "Status byte says not signed")
        self.assertEqual(eMsgIn.getSignatureInfo()['fingerprint'], self.test_key)
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())
        
        
    def testEncryptSign(self):
        self.test_str = self.string_generator(690).encode('utf-8')
#         print "Using test string: "+self.test_str

        eMsgOut = extMessageOutgoing(self.test_str, self.split_size, encrypt_key=self.test_key, sign_key=self.test_key)
        eMsgIn = extMessageIncoming(eMsgOut.getFragments()[0])
        for f in eMsgOut.getFragments()[1:]:
            eMsgIn.addFragment(f)
        self.assertTrue(eMsgIn.isComplete())
        self.assertTrue(eMsgIn.isSigned(), "Status byte says not signed")
        self.assertTrue(eMsgIn.isEncrypted(), "Status byte says not encrypted")
        self.assertEqual(eMsgIn.getSignatureInfo()['fingerprint'], self.test_key)
        self.assertEqual(self.test_str, eMsgIn.getPlainMessage())

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()