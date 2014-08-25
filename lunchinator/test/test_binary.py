from lunchinator import convert_raw
from PyQt4.QtCore import QString, QByteArray

def testUTF8Convert(test, s):
    raw = convert_raw(s)
    s2 = unicode(raw, 'utf-8')
    assert s2 == test


uml = u"test\u00dc\xe9"
umlQt = QString(uml)
umlByteArray = bytearray(uml.encode('utf-8'))
umlQByteArray = QByteArray(umlByteArray)

testUTF8Convert(uml, uml)
testUTF8Convert(uml, umlQt)
testUTF8Convert(uml, umlByteArray)
testUTF8Convert(uml, umlQByteArray)

def testBinConvert(test, s):
    binary = convert_raw(s)
    b = bytearray(binary)
    assert test == b

binary = bytearray()
for i in range(255):
    binary += chr(i)
binaryStr = str(binary)
binaryQ = QByteArray(binary)

testBinConvert(binary, binary)
testBinConvert(binary, binaryStr)
testBinConvert(binary, binaryQ)

print "All tests succeeded"