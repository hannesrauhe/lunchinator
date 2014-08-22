from lunchinator import get_db_connection
from lunchinator.log import getLogger
from private_messages.chat_messages_model import ChatMessagesModel

class InconsistentIDError(Exception):
    def __init__(self, validID):
        self.validID = validID

class ChatMessagesStorage(object):
    _DB_VERSION_INITIAL = 0
    _DB_VERSION_RECEIVE_TIME = 1
    _DB_VERSION_NO_NEXTID = 2
    _DB_VERSION_CURRENT = _DB_VERSION_NO_NEXTID
    
    MSG_PARTNER_COL = 0
    MSG_ID_COL = 1
    MSG_IS_OWN_MESSAGE_COL = 2
    MSG_TIME_COL = 3
    MSG_STATUS_COL = 4
    MSG_TEXT_COL = 5
    MSG_RECV_TIME_COL = 6
    
    _MESSAGES_TABLE_STATEMENT = """
       CREATE TABLE PRIVATE_MESSAGES(PARTNER TEXT NOT NULL,
                                     M_ID INTEGER NOT NULL,
                                     IS_OWN_MESSAGE BOOLEAN NOT NULL,
                                     TIME REAL NOT NULL,
                                     STATUS INTEGER,
                                     MESSAGE TEXT,
                                     RECV_TIME REAL,
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

    _RECENT_UNDELIVERED_MESSAGES_FOR_PARTNER_SQL = """
        select *
        from private_messages p1
        where p1.partner = ? and p1.status = 1 and not exists (
            select 1
            from private_messages p2
            where p1.partner = p2.partner and
                  p2.status = 0 and
                  p2.m_id > p1.m_id
        )
    """
    
    def __init__(self):
        self._db, plugin_type = get_db_connection()
        
        if self._db == None:
            getLogger().error("Unable to get database connection.")
            return
        
        if plugin_type != "SQLite Connection":
            getLogger().warning("Your standard connection is not of type SQLite. " + \
                "Using Private Messages with another type is experimental.")
        
        if not self._db.existsTable("PRIVATE_MESSAGES_VERSION"):
            self._db.execute("CREATE TABLE PRIVATE_MESSAGES_VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO PRIVATE_MESSAGES_VERSION(VERSION) VALUES(?)", self._DB_VERSION_CURRENT)
        
        if not self._db.existsTable("PRIVATE_MESSAGES"):
            self._db.execute(self._MESSAGES_TABLE_STATEMENT)
            self._db.execute("CREATE INDEX PRIVATE_MESSAGE_TIME_INDEX on PRIVATE_MESSAGES(TIME)")
            self._db.execute("CREATE INDEX PRIVATE_MESSAGE_PARTNER_INDEX on PRIVATE_MESSAGES(PARTNER)")
            
        self._checkDBVersion()

    def _getDBVersion(self):
        return self._db.query("SELECT VERSION FROM PRIVATE_MESSAGES_VERSION")[0][0]
    
    def _updateDBVersion(self):
        self._db.execute("UPDATE PRIVATE_MESSAGES_VERSION SET VERSION = ?", self._DB_VERSION_CURRENT)
    
    def _checkDBVersion(self):
        dbVersion = self._getDBVersion()
        if dbVersion == self._DB_VERSION_CURRENT:
            return
        
        if dbVersion == self._DB_VERSION_INITIAL:
            self._db.execute("ALTER TABLE PRIVATE_MESSAGES ADD COLUMN RECV_TIME REAL")
            self._db.execute("UPDATE PRIVATE_MESSAGES SET RECV_TIME = TIME")
            dbVersion = self._DB_VERSION_RECEIVE_TIME
        if dbVersion == self._DB_VERSION_RECEIVE_TIME:
            self._db.execute("DROP TABLE IF EXISTS PRIVATE_MESSAGES_NEXTID")
            dbVersion = self._DB_VERSION_NO_NEXTID
        
        self._updateDBVersion()    
    
    def addOwnMessage(self, msgID, partner, msgTime, msgState, msg, recvTime=None):
        self._db.execute("INSERT INTO PRIVATE_MESSAGES VALUES(?, ?, ?, ?, ?, ?, ?)",
                         partner,
                         msgID,
                         True,
                         msgTime,
                         msgState,
                         msg,
                         recvTime)
        
    def addOtherMessage(self, msgID, partner, msgTime, msg, recvTime):
        self._db.execute("INSERT INTO PRIVATE_MESSAGES VALUES(?, ?, ?, ?, ?, ?, ?)",
                         partner,
                         msgID,
                         False,
                         msgTime,
                         ChatMessagesModel.MESSAGE_STATE_OK,
                         msg,
                         recvTime)
        
    def getMessageState(self, otherID, msgID):
        rows = self._db.query("SELECT STATUS FROM PRIVATE_MESSAGES WHERE M_ID = ? AND PARTNER = ? AND IS_OWN_MESSAGE = ?", msgID, otherID, True)
        if len(rows) == 0:
            return None
        
        return rows[0][0]

    def updateMessageState(self, msgID, newState):
        self._db.execute("UPDATE PRIVATE_MESSAGES SET STATUS=? WHERE M_ID = ? AND IS_OWN_MESSAGE = ?", newState, msgID, True)
        
    def getReceiveTime(self, partner, msgID):
        rows = self._db.query("SELECT RECV_TIME FROM PRIVATE_MESSAGES WHERE PARTNER = ? AND M_ID = ?", partner, msgID)
        if len(rows) > 0:
            return rows[0][0]
        return None
        
    def updateReceiveTime(self, partner, msgID, recvTime):
        self._db.execute("UPDATE PRIVATE_MESSAGES SET RECV_TIME=? WHERE PARTNER = ? AND M_ID = ?", recvTime, partner, msgID)
      
    def getMessage(self, partner, msgID, ownMessage):
        rows = self._db.query("SELECT * FROM PRIVATE_MESSAGES WHERE PARTNER = ? AND M_ID = ? AND IS_OWN_MESSAGE=?", partner, msgID, ownMessage)
        if len(rows) > 0:
            return rows[0]
        return None
    
    def updateMessageID(self, partner, oldID, newID, ownMessage):
        try:
            self._db.execute("UPDATE PRIVATE_MESSAGES SET M_ID = ? WHERE PARTNER = ? AND M_ID = ? AND IS_OWN_MESSAGE = ?", newID, partner, oldID, ownMessage)
            return True
        except:
            return False
      
    def containsMessage(self, partner, msgID, msgHTML, sendTime, ownMessage):
        msgTuple = self.getMessage(partner, msgID, ownMessage)
        if msgTuple is not None:
            dbHTML = msgTuple[self.MSG_TEXT_COL]
            dbSendTime = msgTuple[self.MSG_TIME_COL]
            if (sendTime is not None and dbSendTime != sendTime) or dbHTML != msgHTML:
                lastID = self.getLastReceivedMessageID(partner)
                raise InconsistentIDError(lastID + 1)
            return True
        return False
      
    def deleteMessagesForPartner(self, partner):
        if not partner:
            raise Exception("No partner provided")
        
        self._db.query("DELETE FROM PRIVATE_MESSAGES WHERE PARTNER = ?", partner)
        
    def getPreviousMessages(self, partner, numMessages):
        return self._db.query("SELECT * FROM PRIVATE_MESSAGES WHERE PARTNER = ? ORDER BY TIME DESC LIMIT ?", partner, numMessages)
    
    def getMessages(self, partner):
        return self._db.query("SELECT * FROM PRIVATE_MESSAGES WHERE PARTNER = ? ORDER BY TIME DESC", partner)
        
    def getPartners(self):
        if self._db is None:
            return []
        return self._db.query("SELECT DISTINCT PARTNER FROM PRIVATE_MESSAGES ORDER BY PARTNER ASC")
        
    def getRecentUndeliveredMessages(self, partner=None):
        """Returns recent undelivered (outgoing) messages to all partners.
        
        For each partner, returns the most recent messages that have
        not been delivered, if there does not exist a newer message that
        has been delivered.
        
        partner - specify a certain chat partner
        """
        if self._db is None:
            return []
        
        if partner == None:
            return self._db.query(self._RECENT_UNDELIVERED_MESSAGES_SQL)
        else:
            return self._db.query(self._RECENT_UNDELIVERED_MESSAGES_FOR_PARTNER_SQL, partner)
    
    def clearHistory(self, partner):
        self._db.execute("DELETE FROM PRIVATE_MESSAGES WHERE PARTNER = ?", partner)
        
    def getLastSentMessageID(self):
        """Backwards compatibility: On first initialization, next message ID
        will be obtained the old, error-prone way."""
        if self._db is None:
            return -1
        
        rows = self._db.query("SELECT MAX(M_ID) FROM PRIVATE_MESSAGES WHERE IS_OWN_MESSAGE = ?", True)
        if not rows or rows[0][0] == None:
            return -1
        else:
            return rows[0][0]
        
    def getLastReceivedMessageID(self, partner):
        """Returns the last received message ID from a chat partner."""
        rows = self._db.query("SELECT MAX(M_ID) FROM PRIVATE_MESSAGES WHERE PARTNER = ? AND IS_OWN_MESSAGE = ?", partner, False)
        if not rows or rows[0][0] == None:
            return -1
        else:
            return rows[0][0]
        
