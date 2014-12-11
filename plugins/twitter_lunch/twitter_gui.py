import os, webbrowser, re
from PyQt4.QtGui import QGridLayout, QWidget
from PyQt4.QtCore import QTimer
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtNetwork import QNetworkProxy
from lunchinator import get_settings
from PyQt4.Qt import QLabel, QTextEdit, QPushButton

class TwitterGui(QWidget):    
    URL_REGEX = re.compile(r'''((?:mailto:|ftp://|http://|https://)[^ <>'"{}|\\^`[\]]*)''')
    
    def __init__(self, parent, connPlugin, logger, db_conn):
        super(TwitterGui, self).__init__(parent)
        self._db_conn = db_conn
        self.logger = logger
        self._connPlugin = connPlugin
        self._last_m_id = 0
        
        lay = QGridLayout(self)
        self.msgview = QWebView(self)
        if get_settings().get_proxy():
            proxy = QNetworkProxy()
            
            proxy.setType(QNetworkProxy.HttpProxy)
            proxy.setHostName('localhost');
            proxy.setPort(3128)
            QNetworkProxy.setApplicationProxy(proxy);
        self.msgview.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.msgview.linkClicked.connect(self.linkClicked)
                
        self.post_field = QTextEdit(self)
        self.post_field.setMaximumHeight(50)
        self.send_button = QPushButton("Post", self)
        self.send_button.clicked.connect(self.postStatusClicked)
        
        lay.addWidget(self.msgview, 0, 0, 1, 2)
        lay.addWidget(self.post_field, 1, 0, 1, 1)
        lay.addWidget(self.send_button, 1, 1, 1, 1)
        
        self.timer  = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.update_view)
        
    def start(self):
        self.update_view()
        self.timer.start()
        
    def stop(self):
        self.timer.stop()
        
    def update_view(self):
        template_file_path = os.path.join(get_settings().get_main_config_dir(),"tweet.thtml")
        
        tweets = self._db_conn.get_last_tweets(self._last_m_id)
        if len(tweets)==0:
            return 0
        self._last_m_id = tweets[0][4]
        
        templ_text = '<div>\
                    <a href="http://twitter.com/$NAME$/status/$ID$">\
                            <img src="$IMAGE$" style="float: left; margin-right: 2px" alt="$NAME$" title="$NAME$"/>\
                    </a>\
                    <p>$TEXT$</p>\
                    </div>\
                    <hr style="clear: both" />\
                    '
        if os.path.exists(template_file_path):
            t_file = open(template_file_path, "r")
            templ_text = t_file.read()
            t_file.close()
            
        
        txt = ""
        for t in tweets:
            text = self.URL_REGEX.sub(r'<a href="\1">\1</a>', t[0])
            t_txt = templ_text.replace("$IMAGE$", t[2]).replace("$NAME$", t[1]).replace("$ID$", str(t[4])).replace("$TEXT$", text)
            txt += t_txt

        self.msgview.setHtml(txt)
        
    def linkClicked(self, url): 
        webbrowser.open(str(url.toString()))
        
    def postStatusClicked(self):
        msg = unicode(self.post_field.toPlainText().toUtf8(), encoding="UTF-8")
        if msg:
            self._db_conn.insert_post_queue(msg)