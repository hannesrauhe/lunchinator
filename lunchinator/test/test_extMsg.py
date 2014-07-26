'''
Created on 25.07.2014

@author: Hannes Rauhe
'''
import unittest, random, string
from lunchinator.lunch_socket import *

class extMsgTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass
    
    def string_generator(size=6, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))
    
    def testCompression(self):
        extMessageOutgoing(self.string_generator(690))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()