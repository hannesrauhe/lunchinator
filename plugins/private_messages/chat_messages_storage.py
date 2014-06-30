from lunchinator.logging_mutex import loggingMutex
from lunchinator import get_settings, get_db_connection, log_warning, log_error
from private_messages.chat_messages_model import ChatMessagesModel

class ChatMessagesStorage(object):
    _DB_VERSION_INITIAL = 0
    _DB_VERSION_CURRENT = _DB_VERSION_INITIAL
    
    _MESSAGES_TABLE_STATEMENT = """
       CREATE TABLE PRIVATE_MESSAGES(PARTNER TEXT NOT NULL,
                                     M_ID INTEGER NOT NULL,
                                     IS_OWN_MESSAGE BOOLEAN NOT NULL,
                                     TIME REAL NOT NULL,
                                     STATUS INTEGER,
                                     MESSAGE TEXT,
                                     PRIMARY KEY(PARTNER, M_ID, IS_OWN_MESSAGE)
                                    )
    """
                                    
    _RECENT_UNDELIVERED_MESSAGES_SQL = """
        select *
        from private_messages p1
        where p1.status = 1 and not exists (
            select 1
            from private_messages p2
            where p1.partner = p2.partner and
                  p2.status = 0 and
                  p2.m_id > p1.m_id
        )
    """
    
    def __init__(self):
        self._lock = loggingMutex("chat messages storage", logging=get_settings().get_verbose())
        self._db, plugin_type = get_db_connection()
        
        if self._db == None:
            log_error("Unable to get database connection.")
            return
        
        if plugin_type != "SQLite Connection":
            log_warning("Your standard connection is not of type SQLite. " + \
                "Using Private Messages with another type is experimental.")
        
        if not self._db.existsTable("PRIVATE_MESSAGES_VERSION"):
            self._db.execute("CREATE TABLE PRIVATE_MESSAGES_VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO PRIVATE_MESSAGES_VERSION(VERSION) VALUES(?)", self._DB_VERSION_CURRENT)
                        
        if not self._db.existsTable("PRIVATE_MESSAGES"):
            self._db.execute(self._MESSAGES_TABLE_STATEMENT)
            self._db.execute("CREATE INDEX PRIVATE_MESSAGE_TIME_INDEX on PRIVATE_MESSAGES(TIME)")
            self._db.execute("CREATE INDEX PRIVATE_MESSAGE_PARTNER_INDEX on PRIVATE_MESSAGES(PARTNER)")

    def _getDBVersion(self):
        return self._db.query("SELECT VERSION FROM CORE_MESSAGE_VERSION")[0][0]
    
    def addOwnMessage(self, msgID, partner, msgTime, msgState, msg):
        self._db.execute("INSERT INTO PRIVATE_MESSAGES VALUES(?, ?, ?, ?, ?, ?)",
                         partner,
                         msgID,
                         True,
                         msgTime,
                         msgState,
                         msg)
        
    def addOtherMessage(self, msgID, partner, msgTime, msg):
        self._db.execute("INSERT INTO PRIVATE_MESSAGES VALUES(?, ?, ?, ?, ?, ?)",
                         partner,
                         msgID,
                         False,
                         msgTime,
                         ChatMessagesModel.MESSAGE_STATE_OK,
                         msg)
        
    def getMessageState(self, otherID, msgID):
        rows = self._db.query("SELECT STATUS FROM PRIVATE_MESSAGES WHERE M_ID = ? AND PARTNER = ? AND IS_OWN_MESSAGE = ?", msgID, otherID, True)
        if len(rows) == 0:
            return None
        
        return rows[0][0]

    def updateMessageState(self, msgID, newState):
        self._db.execute("UPDATE PRIVATE_MESSAGES SET STATUS=? WHERE M_ID = ? AND IS_OWN_MESSAGE = ?", newState, msgID, True)
        
    def getNextMessageID(self):
        rows = self._db.query("SELECT MAX(M_ID) FROM PRIVATE_MESSAGES WHERE IS_OWN_MESSAGE = ?", True)
        if not rows or rows[0][0] == None:
            return 0
        return rows[0][0] + 1
      
    def containsMessage(self, partner, msgID):
        rows = self._db.query("SELECT 1 FROM PRIVATE_MESSAGES WHERE PARTNER = ? AND M_ID = ?", partner, msgID)
        return len(rows) > 0
      
    def deleteMessagesForPartner(self, partner):
        if not partner:
            raise Exception("No partner provided")
        
        self._db.query("DELETE FROM PRIVATE_MESSAGES WHERE PARTNER = ?", partner)
        
    def getPreviousMessages(self, partner, numMessages):
        return self._db.query("SELECT * FROM PRIVATE_MESSAGES WHERE PARTNER = ? ORDER BY TIME DESC LIMIT ?", partner, numMessages)
        
    def getRecentUndeliveredMessages(self):
        """Returns recent undelivered (outgoing) messages to all partners.
        
        For each partner, returns the most recent messages that have
        not been delivered, if there does not exist a newer message that
        has been delivered.
        """
        return self._db.query(self._RECENT_UNDELIVERED_MESSAGES_SQL)
    