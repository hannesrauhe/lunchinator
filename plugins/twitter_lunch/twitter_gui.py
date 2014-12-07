from PyQt4.QtGui import QGridLayout, QWidget, QTextEdit
from PyQt4.QtWebKit import QWebView

class TwitterGui(QWidget):    
    def __init__(self, parent, connPlugin, logger, db_conn):
        super(TwitterGui, self).__init__(parent)
        self._db_conn = db_conn
        self.logger = logger
        self.connPlugin = connPlugin
        
        lay = QGridLayout(self)
        self.msgview = QWebView(self)
        lay.addWidget(self.msgview, 0, 0, 1, 2)
        
        tweets = db_conn.get_last_tweets()
        txt = ""
        for t in tweets:
            txt += "<div><img src=\"%s\"/><p>@%s: %s</p></div>"%(t[2], t[1], t[0])
        self.msgview.setHtml(txt)