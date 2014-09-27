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
    
def testURL(matcher, url):
    testMatch(matcher, url, [url])
    testMatch(matcher, u"This is some text, this is a URL: " + url, [url])
    testMatch(matcher, url + u" <- this was a URL", [url])
    testMatch(matcher, u"There is a URL: " + url + u" in the middle", [url])
    testMatch(matcher, url + u" test " + url + u" test " + url, [url, url, url])
    
def testBaseURL(matcher, baseURL):
    testURL(matcher, u"www." + baseURL)
    testURL(matcher, u"http://" + baseURL)
    testURL(matcher, u"http://www." + baseURL)
    
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

matcher = ChatWidget._MAIL_MATCHER
testURL(matcher, u"asdf@foo.bar")
testURL(matcher, u"asdf.foo@foo.bar")
testURL(matcher, u"asdf-1024@foo.bar")
