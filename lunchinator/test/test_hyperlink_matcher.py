from private_messages.chat_widget import ChatWidget
from lunchinator.log import getLogger

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
            getLogger().warning("Found unexpected URI: %s", match)
            pass
        pos += matcher.matchedLength()
    if len(expectedURIs) > 0:
        getLogger().error("Didn't find %s", expectedURIs)
    
def testBaseURL(matcher, baseURL):
    #testMatch(matcher, baseURL, [baseURL])
    testMatch(matcher, u"www." + baseURL, [u"www." + baseURL])
    testMatch(matcher, u"http://" + baseURL, [u"http://" + baseURL])
    testMatch(matcher, u"http://www." + baseURL, [u"http://www." + baseURL])
        
matcher = ChatWidget._URI_MATCHER
testBaseURL(matcher, "google.de")
testBaseURL(matcher, "google.de/foo/bar")
testBaseURL(matcher, "google.de:8080")
testBaseURL(matcher, "google.de:8080/")
testBaseURL(matcher, "google.de:8080/foo/bar")
testBaseURL(matcher, "google.de:8080/foo/bar#test")
testBaseURL(matcher, "google.de:8080/foo/bar?search")
testBaseURL(matcher, "google.de:8080/foo/bar?search#anchor")
