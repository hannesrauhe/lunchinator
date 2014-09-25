from private_messages.chat_widget import ChatWidget
from lunchinator.log import getCoreLogger, initializeLogger

def testMatch(matcher, text, expectedURIs):
    pos = 0
    while pos != -1:
        pos = matcher.indexIn(text, pos)
        if pos == -1:
            break
        
        match = text[pos:pos+matcher.matchedLength()]
        try:
            expectedURIs.remove(match)
        except:
            getCoreLogger().warning("Found unexpected URI: %s", match)
            pass
        pos += matcher.matchedLength()
    if len(expectedURIs) > 0:
        getCoreLogger().error("Didn't find %s", expectedURIs)
    
def testBaseURL(matcher, baseURL):
    #testMatch(matcher, baseURL, [baseURL])
    testMatch(matcher, u"www." + baseURL, [u"www." + baseURL])
    testMatch(matcher, u"http://" + baseURL, [u"http://" + baseURL])
    testMatch(matcher, u"http://www." + baseURL, [u"http://www." + baseURL])
    
initializeLogger()
        
matcher = ChatWidget._URI_MATCHER
testBaseURL(matcher, "google.de")
testBaseURL(matcher, "google.de/foo/bar")
testBaseURL(matcher, "google.de:8080")
testBaseURL(matcher, "google.de:8080/")
testBaseURL(matcher, "google.de:8080/foo/bar")
testBaseURL(matcher, "google.de:8080/foo/bar#test")
testBaseURL(matcher, "google.de:8080/foo/bar?search")
testBaseURL(matcher, "google.de:8080/foo/bar?search#anchor")
testBaseURL(matcher, "amazon.de/asdf-we-r-tr-t-/qw/Bo28374aSEF2/ref=ztrz_45_67?ie=UTF8&qid=46546878798789&sr=8-1&keywords=some+keywords")
