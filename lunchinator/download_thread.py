from PySide.QtCore import QThread, Signal
from lunchinator import log_exception
import urllib2, contextlib
from cStringIO import StringIO, OutputType
   
class DownloadThread(QThread):
    success = Signal(QThread, unicode)
    error = Signal(QThread, unicode)
    
    def __init__(self, parent, url, target = None):
        super(DownloadThread, self).__init__(parent)
        self.url = url
        if target == None:
            self.target = StringIO()
        else:
            self.target = target

    def getResult(self):
        if type(self.target) is OutputType:
            return self.target.getvalue()
        else:
            raise Exception("Cannot get the value from target of type %s" % type(self.target))

    def run(self):
        try:
            with contextlib.closing(urllib2.urlopen(self.url)) as u:
                self.target.write(u.read())
                self.success.emit(self, self.url)
        except:
            log_exception("TDT notify error while downloading")
            self.error.emit(self, self.url)