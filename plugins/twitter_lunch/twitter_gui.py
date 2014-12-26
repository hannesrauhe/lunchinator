import os, webbrowser, re, time, urlparse
from PyQt4.QtGui import QGridLayout, QVBoxLayout, QWidget
from PyQt4.QtCore import QTimer
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtNetwork import QNetworkProxy
from lunchinator import get_settings, convert_string
from PyQt4.Qt import QLabel, QTextEdit, QPushButton, QComboBox, QUrl, pyqtSlot,\
    QString

class TwitterGui(QWidget):    
    URL_REGEX = re.compile(r'''((?:mailto:|ftp://|http://|https://)[^ <>'"{}|\\^`[\]]*)''')
    
    def __init__(self, parent, logger, db_conn, update_func, safe_conn):
        super(TwitterGui, self).__init__(parent)
        self._db_conn = db_conn
        self.logger = logger
        self._reply_to_id = 0
        self._update_func = update_func
        
        if get_settings().get_proxy():
            u = urlparse.urlsplit(get_settings().get_proxy())
            proxy = QNetworkProxy()
            
            proxy.setType(QNetworkProxy.HttpProxy)
            proxy.setHostName(u.hostname);
            proxy.setPort(u.port)
            QNetworkProxy.setApplicationProxy(proxy);
        
        self.msgview = QWebView(self)
        self.msgview.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.msgview.linkClicked.connect(self.link_clicked)
        
        self.showButton = QPushButton(chr(94), self)  
        self.showButton.setMaximumHeight(13)
        self.showButton.clicked.connect(self.show_hide_animation)
        self.post_field = QTextEdit(self)
        self.post_field.setMaximumHeight(50)
        self.post_field.textChanged.connect(self.text_changed)
        self.send_button = QPushButton("Post", self)
        self.send_button.clicked.connect(self.post_status_clicked)
        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self._update_func)
        self.attach_button = QPushButton("Attach", self)
        self.attach_button.clicked.connect(lambda _ : self.set_status("Attach something"))
        self.lists_box = QComboBox(self)
        self.lists_box.currentIndexChanged.connect(self.list_changed)
        self.lists_box.setEditable(False)
        self.lists_box.addItems([u"Home"] + self._db_conn.get_lists())
        self.statusLabel = QLabel("Status", self)
        self.charCounter = QLabel("0", self)
        
        self.gridw = QWidget(self)
        self.gridw.setContentsMargins(0, 0, 0, 0)
        gridlay = QGridLayout(self.gridw)
        gridlay.setContentsMargins(0, 0, 0, 0)
        gridlay.addWidget(self.post_field, 0, 0, 2, 1)
        gridlay.addWidget(self.attach_button, 0, 1, 1, 1)
        gridlay.addWidget(self.send_button, 1, 1, 1, 1)
        gridlay.addWidget(self.refresh_button, 0, 2, 1, 1)
        gridlay.addWidget(self.lists_box, 1, 2, 1, 1)
        gridlay.addWidget(self.statusLabel, 2, 0, 1, 1)
        gridlay.addWidget(self.charCounter, 2, 1, 1, 2)
        
        hlay = QVBoxLayout(self)
        hlay.addWidget(self.msgview)
        hlay.addWidget(self.showButton)
        hlay.addWidget(self.gridw)
        
        self._list = None
        
        safe_conn.connect_home_timeline_updated(self.update_view)
        safe_conn.connect_twitter_loop_started(self.start_refresh_animation)
        safe_conn.connect_twitter_loop_stopped(self.stop_refresh_animation)
        safe_conn.connect_update_posted(self.enable_posting)
        safe_conn.connect_range_limit_exceeded(lambda _ : self.set_status("Range limit exceeded"))
        safe_conn.connect_not_authenticated(lambda _ : self.set_status("Authentication failed"))
        
        self.gridw.hide()
        self.update_view()
        self.set_status("Twitter plugin initialized")
        
    def enable_posting(self, q_id, m_id):
        if m_id>1:
            self.post_field.setText("")
            self.set_status("Tweet posted")
        else:
            self.set_status("Failed to post tweet, Error: " + str(abs(m_id)))
        self.post_field.setEnabled(True)
        
    def link_clicked(self, url):
        if not url.host():
            if url.hasQueryItem("reply-to") and url.hasQueryItem("screen-name"):
                self._reply_to_id = long(convert_string(url.queryItemValue("reply-to")))
                self.post_field.setPlainText("@"+convert_string(url.queryItemValue("screen-name"))+" ")
                self.set_status("Reply to @"+convert_string(url.queryItemValue("screen-name")))
            else:
                self.logger.error("Unknown command from link: "+str(url.toString()))
        else:
            webbrowser.open(str(url.toString()))
            
    def list_changed(self, list_idx):
        if list_idx:
            self._list = convert_string(self.lists_box.currentText())
            self.set_status(self._list)
        else:
            self._list = None
        self.update_view()
        
    def post_status_clicked(self):
        msg = unicode(self.post_field.toPlainText().toUtf8(), encoding="UTF-8")
        if msg:
            self._db_conn.insert_post_queue(msg, self._reply_to_id)
            self._reply_to_id = 0
            self._update_func()
            self.post_field.setDisabled(True)
    
    def start_refresh_animation(self):
        self.refresh_button.setDisabled(True)
    
    def stop_refresh_animation(self):
        self.refresh_button.setEnabled(True)
        
    def show_hide_animation(self):
        if self.gridw.isHidden():
            self.gridw.show()            
            self.showButton.setText("v")
        else:
            self.gridw.hide()
            self.showButton.setText(chr(94))
            
    def text_changed(self):
        count = len(self.post_field.toPlainText())
        if count==0:
            self._reply_to_id = 0
        if self._reply_to_id:
            self.charCounter.setText(str(count) + " - reply to ")
        else:
            self.charCounter.setText(str(count))
        
    @pyqtSlot(object)
    def update_view(self, _ = None):
        template_file_path = os.path.join(get_settings().get_main_config_dir(),"tweet.thtml")
        
        tweets = self._db_conn.get_last_tweets(user_list = self._list)
        if len(tweets)==0:
            return 0
        
        templ_text = '<div>\
                    <a href="http://twitter.com/$NAME$/status/$ID$">\
                            <img src="$IMAGE$" style="float: left; margin-right: 2px" alt="$NAME$" title="$NAME$"/>\
                    </a>\
                    <p>$TEXT$</p>\
                    <span><a href="http://twitter.com/$RT_USER$">$RT_USER$</a></span>\
                    <span style="float: right">$CREATE_TIME$ <a href="?retweet=$ID$">retweet</a> <a href="?reply-to=$ID$&screen-name=$NAME$">reply</a></span>\
                    </div>\
                    <hr style="clear: both" />\
                    '
        if os.path.exists(template_file_path):
            t_file = open(template_file_path, "r")
            templ_text = t_file.read()
            t_file.close()
        
        txt = ""
        for t in tweets:
            """m_id, screen_name, user_image, create_time, message_text, retweeted_by"""
            text = self.URL_REGEX.sub(r'<a href="\1">\1</a>', t[4])
            t_txt = templ_text.replace("$IMAGE$", t[2]).replace("$NAME$", t[1])
            t_txt = t_txt.replace("$ID$", str(t[0])).replace("$TEXT$", text)
            t_txt = t_txt.replace("$CREATE_TIME$", self.humanReadableTime(t[3]))
            t_txt = t_txt.replace("$RT_USER$", t[5])
            txt += t_txt
        txt += "<p style=\"float:right\">Updated: %s</p>"%time.strftime("%H:%M")

        self.msgview.setHtml(txt)
        
            
    """helper:"""
    def set_status(self, status_text):
        self.statusLabel.setText(status_text)
        self.showButton.setToolTip(status_text)
    
    def humanReadableTime(self, post_time):
        fudge = 1.25
        delta = long(time.time()) - long(post_time)
    
        if delta < (1 * fudge):
            return 'about a second ago' 
        elif delta < (60 * (1 / fudge)):
            return 'about %d seconds ago' % (delta)
        elif delta < (60 * fudge):
            return 'about a minute ago'
        elif delta < (60 * 60 * (1 / fudge)):
            return 'about %d minutes ago' % (delta / 60)
        elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
            return 'about an hour ago'
        elif delta < (60 * 60 * 24 * (1 / fudge)):
            return 'about %d hours ago' % (delta / (60 * 60))
        elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
            return 'about a day ago'
        else:
            return 'about %d days ago' % (delta / (60 * 60 * 24))