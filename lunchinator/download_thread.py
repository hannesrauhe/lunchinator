from PyQt4.QtCore import QThread, pyqtSignal
from lunchinator import log_exception, log_error
import urllib2, contextlib
from cStringIO import StringIO, OutputType
from urllib2 import HTTPError
   
class DownloadThread(QThread):
    success = pyqtSignal(QThread, unicode)
    error = pyqtSignal(QThread, unicode)
    
    def __init__(self, parent, url, target = None, no_proxy = False):
        super(DownloadThread, self).__init__(parent)
        self.url = url
        if target == None:
            self.target = StringIO()
        else:
            self.target = target
        self._no_proxy = no_proxy

    def getResult(self):
        if type(self.target) is OutputType:
            return self.target.getvalue()
        else:
            raise Exception("Cannot get the value from target of type %s" % type(self.target))

    def run(self):
        try:
            if self._no_proxy:
                proxy_handler = urllib2.ProxyHandler({})
                opener = urllib2.build_opener(proxy_handler)                
                with contextlib.closing(opener.open(self.url)) as u:
                    self.target.write(u.read())
                    self.success.emit(self, self.url)
            else:
                with contextlib.closing(urllib2.urlopen(self.url)) as u:
                    self.target.write(u.read())
                    self.success.emit(self, self.url)
        except HTTPError as e:
            # don't print trace on HTTP error
            log_error("Error while downloading %s (%s)"%(self.url, e))
            self.error.emit(self, self.url)
        except:
            log_exception("Error while downloading %s"%self.url)
            self.error.emit(self, self.url)