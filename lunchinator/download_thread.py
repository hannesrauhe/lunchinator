from PyQt4.QtCore import QThread, pyqtSignal
from cStringIO import StringIO, OutputType
import urllib2, contextlib
from urllib2 import HTTPError
from lunchinator.utilities import formatException
   
class DownloadThread(QThread):
    success = pyqtSignal(QThread, object)
    error = pyqtSignal(QThread, object) # self, error msg
    progressChanged = pyqtSignal(QThread, int)
    CHUNK_SIZE = 1024
    NUMBER_OF_TRIES = 5
    TIMEOUT = 3
    
    def __init__(self, parent, logger, url, target=None, no_proxy=False, progress=False):
        super(DownloadThread, self).__init__(parent)
        self.logger = logger
        self.url = url
        self.progress = progress
        if target == None:
            self.target = StringIO()
        else:
            self.target = target
        self._no_proxy = no_proxy

    def getResult(self):
        if type(self.target) is OutputType:
            return self.target.getvalue()
        else:
            return self.target
            # raise Exception("Cannot get the value from target of type %s" % type(self.target))

    def _readData(self, u):
        if self.progress and "content-length" in u.info():
            size = int(u.info()["content-length"])
            prog = 0
            down = 0.
            
            self.progressChanged.emit(self, 0)
            while True:
                data = u.read(self.CHUNK_SIZE)
                self.target.write(data)
                if len(data) < self.CHUNK_SIZE:
                    # finished
                    self.success.emit(self, self.url)
                    break
                down += len(data)
                if int(100 * down / size) > prog:
                    prog = int(100 * down / size)
                    self.progressChanged.emit(self, prog) 
                
            self.progressChanged.emit(self, 100)
        else:
            self.target.write(u.read())
            self.success.emit(self, self.url)

    def run(self):
        nTries = 0
        while nTries < self.NUMBER_OF_TRIES:
            if nTries > 0:
                self.target.seek(0)
                QThread.sleep(self.TIMEOUT)
            nTries += 1
            
            #try standard first (with proxy if environment variable is set)
            try:
                if not self._no_proxy:
                    try:
                        hdr = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
                        req = urllib2.Request(self.url.encode('utf-8'), headers=hdr)
                        with contextlib.closing(urllib2.urlopen(req)) as u:
                            self._readData(u)
                        break
                    except urllib2.URLError:
                        #very likely a proxy error
                        self.logger.debug("Downloading %s failed, forcing without proxy now", self.url)
            
                #try again without proxy
                req2 = urllib2.Request(self.url.encode('utf-8'), headers=hdr)
                proxy_handler = urllib2.ProxyHandler({})
                no_proxy_opener = urllib2.build_opener(proxy_handler)
                with contextlib.closing(no_proxy_opener.open(req2)) as n_u:
                    self._readData(n_u)
                                    
                # finished
                break
            except HTTPError as e:
                # don't print trace on HTTP error
                self.logger.warning("Error while downloading %s (%s)", self.url, e)
                if nTries >= self.NUMBER_OF_TRIES or e.code == 404:
                    self.error.emit(self, formatException())
                    
                if e.code == 404:
                    # no need to retry
                    break
            except:
                self.logger.warning("Error while downloading %s", self.url)
                self.error.emit(self, formatException())
                break

    def close(self):
        self.target.close()