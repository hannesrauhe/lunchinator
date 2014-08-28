from lunchinator import get_db_connection, convert_string, get_settings
from PyQt4.QtCore import QSettings
from time import time
from lunchinator.privacy import PrivacySettings

class RemotePicturesStorage(object):
    _DB_VERSION_LEGACY = 0
    _DB_VERSION_INITIAL = 1
    _DB_VERSION_CURRENT = _DB_VERSION_INITIAL
    
    PIC_CAT_COL = 0
    PIC_URL_COL = 1
    PIC_DESC_COL = 2
    PIC_FILE_COL = 3
    PIC_ADDED_COL = 4
    PIC_SEEN_COL = 5
    PIC_SENDER_COL = 6
    _PIC_LAST_COL = PIC_SENDER_COL
    
    CAT_TITLE_COL = 0
    CAT_THUMBNAIL_COL = 1
    CAT_HIDDEN_COL = 2
    
    _PICTURES_TABLE_STATEMENT = """
       CREATE TABLE REMOTE_PICTURES(CAT TEXT NOT NULL REFERENCES REMOTE_PICTURES_CATEGORY(TITLE),
                                    URL TEXT,
                                    DESC TEXT,
                                    FILE TEXT,
                                    ADDED REAL NOT NULL,
                                    SEEN REAL,
                                    SENDER TEXT)
    """
    
    _CATEGORIES_TABLE_STATEMENT = """
       CREATE TABLE REMOTE_PICTURES_CATEGORY(TITLE TEXT UNIQUE PRIMARY KEY NOT NULL,
                                             THUMBNAIL TEXT,
                                             HIDDEN BOOLEAN NOT NULL)
    """
    
    def __init__(self, delegate, logger):
        self._delegate = delegate
        self.logger = logger
        self._db, plugin_type = get_db_connection(self.logger)
        
        if self._db == None:
            self.logger.error("Unable to get database connection.")
            return
        
        if plugin_type != "SQLite Connection":
            self.logger.warning("Your standard connection is not of type SQLite. " + \
                "Using Remote Pictures with another type is experimental.")
        
        self._checkDBVersion()

    def _getDBVersion(self):
        return self._db.query("SELECT VERSION FROM REMOTE_PICTURES_VERSION")[0][0]
    
    def _updateDBVersion(self):
        self._db.execute("UPDATE REMOTE_PICTURES_VERSION SET VERSION = ?", self._DB_VERSION_CURRENT)
    
    def _checkDBVersion(self):
        if not self._db.existsTable("REMOTE_PICTURES_VERSION"):
            self._db.execute("CREATE TABLE REMOTE_PICTURES_VERSION(VERSION INTEGER)")
            self._db.execute("INSERT INTO REMOTE_PICTURES_VERSION(VERSION) VALUES(?)", self._DB_VERSION_CURRENT)
        
        if not self._db.existsTable("REMOTE_PICTURES") or not self._db.existsTable("REMOTE_PICTURES"):
            self._db.execute("DROP TABLE IF EXISTS REMOTE_PICTURES")
            self._db.execute("DROP TABLE IF EXISTS REMOTE_PICTURES_CATEGORY")
            self._db.execute(self._CATEGORIES_TABLE_STATEMENT)
            self._db.execute(self._PICTURES_TABLE_STATEMENT)
            self._db.execute("CREATE INDEX REMOTE_PICTURES_CAT_INDEX on REMOTE_PICTURES(CAT)")
            
            # load legacy index, if exists
            self._loadIndex()
            
    def _addCategory(self, title, thumbnail, hidden=False):
        if self._db is None:
            self.logger.error("Cannot add category, no database connection")
            return
        
        if title is None:
            raise ValueError("title cannot be None")
        
        self._db.execute("INSERT INTO REMOTE_PICTURES_CATEGORY VALUES(?, ?, ?)", title, thumbnail, hidden)
        
    def addEmptyCategory(self, title, thumbnail=None, hidden=False):
        """Adds a category to the index that has no pictures yet."""
        self._addCategory(title, thumbnail, hidden)
        
    def addPicture(self, cat, url, desc, localFile, added, seen, sender):
        """Adds a picture and its category, if needed.
        
        Returns True if the category did not exist already and had to be
        created or if this is the first image in a previously empty
        category.
        """
        if self._db is None:
            self.logger.error("Cannot add picture, no database connection")
            return
        
        catAdded = False
        if not self.hasCategory(cat):
            self._addCategory(cat, None)
            catAdded = True
        elif self.isCategoryEmpty(cat):
            catAdded = True
            
        self._db.execute("INSERT INTO REMOTE_PICTURES VALUES(?, ?, ?, ?, ?, ?, ?)", cat, url, desc, localFile, added, seen, sender)
        
        return catAdded
            
    def _loadIndex(self):
        try:
            self.settings = QSettings(get_settings().get_config("remote_pictures", "index"), QSettings.NativeFormat)
                        
            storedThumbnails  = self.settings.value("categoryThumbnails", None)
            if storedThumbnails != None:
                storedThumbnails = storedThumbnails.toMap()
                for aCat in storedThumbnails:
                    thumbnailPath = convert_string(storedThumbnails[aCat].toString())
                    aCat = convert_string(aCat)
                    if aCat == u"Not Categorized":
                        aCat = PrivacySettings.NO_CATEGORY
                    self._addCategory(aCat, thumbnailPath)
                    
            categoryPictures = self.settings.value("categoryPictures", None)
            if categoryPictures != None:
                tmpDict = categoryPictures.toMap()
                added = time()
                for aCat in tmpDict:
                    newKey = convert_string(aCat)
                    if newKey == u"Not Categorized":
                        newKey = PrivacySettings.NO_CATEGORY
                    picTupleList = tmpDict[aCat].toList()
                    for picTuple in picTupleList:
                        tupleList = picTuple.toList()
                        picURL = convert_string(tupleList[0].toString())
                        picDesc = convert_string(tupleList[1].toString())
                        self.addPicture(newKey, picURL, picDesc, None, added, None, None)
                        if not picDesc:
                            picDesc = None
                        
        except:
            self.logger.exception("Could not load thumbnail index.")
    
    def hasCategory(self, cat):
        if self._db is None:
            return False
        
        rows = self._db.query("SELECT 1 FROM REMOTE_PICTURES_CATEGORY WHERE TITLE = ?", cat)
        return len(rows) > 0

    def isCategoryEmpty(self, cat):
        if self._db is None:
            return True
        
        rows = self._db.query("SELECT 1 FROM REMOTE_PICTURES WHERE CAT = ? LIMIT 1", cat)
        return len(rows) == 0

    def getPictureID(self, cat, url):
        if self._db is None:
            return False
        
        if cat is None:
            cat = PrivacySettings.NO_CATEGORY
            
        rows = self._db.query("SELECT ROWID FROM REMOTE_PICTURES WHERE CAT = ? AND URL = ?", cat, url)
        if len(rows) == 0:
            return None
        return rows[0][0]
    
    def hasPicture(self, cat, url):
        return self.getPictureID(cat, url) is not None
    
    def getLatestPicture(self, category):
        """Returns (picture ID, picture row) of the latest picture in a given category or (None, None)."""
        if self._db is None:
            return None, None
        
        rows = self._db.query("SELECT *, ROWID FROM REMOTE_PICTURES P1 WHERE P1.CAT = ? AND NOT EXISTS(SELECT 1 FROM REMOTE_PICTURES P2 WHERE P1.CAT = P2.CAT AND P2.ROWID > P1.ROWID)", category)
        if len(rows) == 0:
            return None, None
        return rows[0][self._PIC_LAST_COL + 1], rows[0]
    
    def getPreviousPicture(self, cat, picID):
        """Returns (picture ID, picture row) of the previous picture of the same category or (None, None)."""
        if self._db is None:
            return None, None
        
        rows = self._db.query("SELECT *, ROWID FROM REMOTE_PICTURES P1 WHERE P1.ROWID < ? AND P1.CAT = ? AND NOT EXISTS(SELECT 1 FROM REMOTE_PICTURES P2 WHERE P1.CAT = P2.CAT AND P2.ROWID > P1.ROWID AND P2.ROWID < ?)", picID, cat, picID)
        if len(rows) == 0:
            return None, None
        return rows[0][self._PIC_LAST_COL + 1], rows[0]
    
    def getNextPicture(self, cat, picID):
        """Returns (picture ID, picture row) of the previous picture of the same category or (None, None)."""
        if self._db is None:
            return None, None
        
        rows = self._db.query("SELECT *, ROWID FROM REMOTE_PICTURES P1 WHERE P1.ROWID > ? AND P1.CAT = ? AND NOT EXISTS(SELECT 1 FROM REMOTE_PICTURES P2 WHERE P1.CAT = P2.CAT AND P2.ROWID < P1.ROWID AND P2.ROWID > ?)", picID, cat, picID)
        if len(rows) == 0:
            return None, None
        return rows[0][self._PIC_LAST_COL + 1], rows[0]
    
    def hasPrevious(self, cat, picID):
        if self._db is None:
            return False
            
        rows = self._db.query("SELECT 1 FROM REMOTE_PICTURES WHERE CAT = ? AND ROWID < ?", cat, picID)
        return len(rows) > 0
    
    def hasNext(self, cat, picID):
        if self._db is None:
            return False
            
        rows = self._db.query("SELECT 1 FROM REMOTE_PICTURES WHERE CAT = ? AND ROWID > ?", cat, picID)
        return len(rows) > 0
    
    def getCategories(self, alsoEmpty=True):
        if self._db is None:
            return []
        
        if alsoEmpty:
            rows = self._db.query("SELECT * FROM REMOTE_PICTURES_CATEGORY")
        else:
            rows = self._db.query("SELECT * FROM REMOTE_PICTURES_CATEGORY C WHERE EXISTS(SELECT 1 FROM REMOTE_PICTURES P WHERE P.CAT = C.TITLE)")
        return sorted(rows, key=lambda row : row[0].lower())
    
    def getCategoryNames(self, alsoEmpty=True):
        if self._db is None:
            return []
        
        categories = self.getCategories(alsoEmpty)
        return [row[0] for row in categories]
    
    def getCategoryThumbnail(self, category):
        if self._db is None:
            return None
        
        rows = self._db.query("SELECT THUMBNAIL FROM REMOTE_PICTURES_CATEGORY WHERE TITLE=?", category)
        if not rows:
            return None
        return rows[0][0]
        
    def setCategoryThumbnail(self, category, thumbnailPath):
        if self._db is None:
            self.logger.error("Cannot set category thumbnail, no database connection")
            return
        
        self._db.execute("UPDATE REMOTE_PICTURES_CATEGORY SET THUMBNAIL=? WHERE TITLE=?", thumbnailPath, category)
        
    def setPictureFile(self, category, url, path):
        if self._db is None:
            self.logger.error("Cannot set picture path, no database connection")
            return
        
        self._db.execute("UPDATE REMOTE_PICTURES SET FILE=? WHERE CAT=? AND URL=? AND FILE IS NULL", path, category, url)
        
    def seenPicture(self, picID):
        if self._db is None:
            return
        
        self._db.execute("UPDATE REMOTE_PICTURES SET SEEN=? WHERE ROWID=?", time(), picID)
        