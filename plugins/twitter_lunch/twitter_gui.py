import os, webbrowser, re
from PyQt4.QtGui import QGridLayout, QWidget
from PyQt4.QtCore import QTimer
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtNetwork import QNetworkProxy
from lunchinator import get_settings

class TwitterGui(QWidget):    
    URL_REGEX = re.compile(r'''((?:mailto:|ftp://|http://|https://)[^ <>'"{}|\\^`[\]]*)''')
    
    def __init__(self, parent, connPlugin, logger, db_conn):
        super(TwitterGui, self).__init__(parent)
        self._db_conn = db_conn
        self.logger = logger
        self.connPlugin = connPlugin
        
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
        
        lay.addWidget(self.msgview, 0, 0, 1, 2)
        
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
        
        tweets = self._db_conn.get_last_tweets()
        if len(tweets)==0:
            return 0
        
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