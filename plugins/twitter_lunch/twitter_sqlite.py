from lunchinator.plugin import db_for_plugin_iface

class twitter_sqlite(db_for_plugin_iface):
    messages_schema = "CREATE TABLE twitter_messages (m_id BIGINT PRIMARY KEY, \
            screen_name TEXT, user_image TEXT, create_time INTEGER, message_text TEXT, retweeted_by TEXT)"
    post_queue_schema = "CREATE TABLE twitter_post_queue (q_id  INTEGER PRIMARY KEY AUTOINCREMENT, \
            message_text TEXT, reply_to BIGINT, create_time INTEGER, m_id BIGINT)"
    lists_schema = "CREATE TABLE twitter_lists (user TEXT, list TEXT)"
    version_schema = "CREATE TABLE twitter_version (commit_count INTEGER, migrate_time INTEGER)"
            
    
    def init_db(self):                   
        if not self.dbConn.existsTable("twitter_version"):
            self.dbConn.execute(self.version_schema)
            self.dbConn.execute("INSERT INTO twitter_version(commit_count, migrate_time) VALUES(?, strftime('%s', 'now'))", 1959)
        if not self.dbConn.existsTable("twitter_messages"):
            self.dbConn.execute(self.messages_schema)
        if not self.dbConn.existsTable("twitter_post_queue"):
            self.dbConn.execute(self.post_queue_schema)
        if not self.dbConn.existsTable("twitter_lists"):
            self.dbConn.execute(self.lists_schema)
    
    def add_user_to_list(self, user, user_list):
        self.dbConn.execute("INSERT INTO twitter_lists(user, list) \
                            VALUES(?, ?)", user, user_list)
        
    def delete_user_from_list(self, user, user_list):
        self.dbConn.execute("DELETE FROM twitter_lists WHERE user=? and list = ?", user, user_list)
        
    def get_lists(self):
        r = self.dbConn.query("Select distinct(list) FROM twitter_lists")
        r = [a[0] for a in r]
        return r
            
    def insert_message(self, tweetAsStatus):
        retweeted_by = ""
        m_id = tweetAsStatus.GetId()
        if tweetAsStatus.GetRetweeted_status():
            retweeted_by = tweetAsStatus.GetUser().GetScreenName()
            tweetAsStatus = tweetAsStatus.GetRetweeted_status()
        created_at = int(tweetAsStatus.GetCreatedAtInSeconds())
        user_name = tweetAsStatus.GetUser().GetScreenName()
        user_pic = tweetAsStatus.GetUser().GetProfileImageUrl()
        tweet_text = tweetAsStatus.GetText()
        self.dbConn.execute("INSERT INTO twitter_messages(m_id, screen_name, user_image, create_time, message_text, retweeted_by) \
                            \nVALUES(?, ?, ?, ?, ?, ?)", m_id, user_name, user_pic, int(created_at), tweet_text, retweeted_by)
        
    def insert_post_queue(self, text, reply_to = 0):
        self.dbConn.execute("INSERT INTO twitter_post_queue(message_text, reply_to, create_time) \
                            VALUES(?, ?, strftime('%s', 'now'))", text, reply_to)        
    
    """return last num tweets (only if anything has happened since min_m_id)"""
    def get_last_tweets(self, num = 20, user_list = None, min_m_id = 0): 
        if min_m_id != 0:
            tmp = []
            if user_list:
                tmp = self.dbConn.query("SELECT m_id \
                                    \n FROM twitter_messages, twitter_messages \
                                    \n WHERE twitter_lists.user=twitter_messages.screen_name \
                                    \n AND twitter_lists.list = ? \
                                    \n WHERE m_id>?", user_list, min_m_id)
            else:
                tmp = self.dbConn.query("SELECT m_id \
                                    \n FROM twitter_messages \
                                    \n WHERE m_id>?", min_m_id)
            if len(tmp)==0:
                return []
        
        r = []
        if user_list:
            r = self.dbConn.query("SELECT twitter_messages.* FROM twitter_lists, twitter_messages \
                                  \n WHERE twitter_lists.user=twitter_messages.screen_name \
                                  \n AND twitter_lists.list = ? \
                                  \n ORDER BY m_id DESC LIMIT ?", user_list, num)
        else:
            r = self.dbConn.query("SELECT * \
                                   \n FROM twitter_messages \
                                   \n ORDER BY m_id DESC LIMIT ?", num)
        return r
    
    def get_unprocessed_queue(self):
        r = self.dbConn.query("SELECT q_id, m_id, message_text \
                                FROM twitter_post_queue \
                                ORDER BY create_time")
        return r
    
    def get_max_id(self):    
        r = self.dbConn.query("SELECT MAX(m_id) FROM twitter_messages")
        if not r:
            return 0
        return r[0][0]
    
    def update_post_queue(self, p_id, m_id, created_at):
        self.dbConn.execute("UPDATE SET created_at=?, m_id=? WHERE p_id=?", created_at, m_id, p_id)