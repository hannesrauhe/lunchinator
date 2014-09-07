from PyQt4.QtGui import QWidget, QComboBox, QHBoxLayout, QLabel, QToolBox,\
    QScrollArea, QFrame, QVBoxLayout
from PyQt4.QtCore import Qt
from privacy_gui.single_category_view import SingleCategoryView
from lunchinator.privacy.privacy_settings import PrivacySettings
from lunchinator import get_notification_center, convert_string
from lunchinator.log.logging_slot import loggingSlot
from itertools import izip

class MultipleCategoriesView(QWidget):
    def __init__(self, action, parent, logger):
        super(MultipleCategoriesView, self).__init__(parent)
        
        self.logger = logger
        self._action = action
        self._mode = PrivacySettings.get().getPolicy(self._action, None, useModified=True, categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        self._currentSingleViews = {}
        self._currentToolBox = None
        
        topView = self._initTopView()
        self._initSettingsWidget()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(topView)
        mainLayout.addWidget(self._settingsWidget, 1)
        self._modeChanged(self._mode, False)
        
        get_notification_center().connectPrivacySettingsChanged(self._privacySettingsChanged)
        get_notification_center().connectPrivacySettingsDiscarded(self._privacySettingsChanged)
        
    def finish(self):
        get_notification_center().disconnectPrivacySettingsChanged(self._privacySettingsChanged)
        get_notification_center().disconnectPrivacySettingsDiscarded(self._privacySettingsChanged)
        self._clearCurrentView()

    def _initTopView(self):
        topWidget = QWidget(self)
        
        self._modeCombo = QComboBox(topWidget)
        self._modeCombo.addItem(u"from nobody")
        self._modeCombo.addItem(u"from nobody, except")
        self._modeCombo.addItem(u"from everybody, except")
        self._modeCombo.addItem(u"from everybody")
        self._modeCombo.addItem(u"depending on category")
        self._modeCombo.setCurrentIndex(self._mode)
        self._modeCombo.currentIndexChanged.connect(self._modeChanged)
        
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.addWidget(QLabel(u"Accept"), 0)
        topLayout.addWidget(self._modeCombo, 1, Qt.AlignLeft)
        return topWidget
    
    def _initSettingsWidget(self):
        self._settingsWidget = QWidget(self)
        layout = QVBoxLayout(self._settingsWidget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
    
    def _clearCurrentView(self):
        for _cat, view in self._currentSingleViews.iteritems():
            view.finish()
        self._currentSingleViews = {}
        
        layout = self._settingsWidget.layout()
        
        child = layout.takeAt(0)
        while child != None:
            child.widget().deleteLater()
            child = layout.takeAt(0)
    
    _PEER_EXCEPTIONS_VIEW = -1
    
    def _createAndInsertSingleView(self, category, index):
        singleView = SingleCategoryView(self._action, self._currentToolBox, category)
        self._currentSingleViews[category] = singleView
        icon = self._action.getCategoryIcon(category)
        title = u"Not Categorized" if category == PrivacySettings.NO_CATEGORY else category
        if icon is not None:
            self._currentToolBox.insertItem(index, singleView, icon, title)
        else:
            self._currentToolBox.insertItem(index, singleView, title)
    
    def _createCategoryView(self):
        self._clearCurrentView()
        
        self._currentToolBox = QToolBox(self)
        self._currentToolBox.setAutoFillBackground(False)
        for category in self._action.getPrivacyCategories():
            self._createAndInsertSingleView(category, -1)
        
        peerExceptions = SingleCategoryView(self._action, self._currentToolBox, category=None, mode=PrivacySettings.POLICY_PEER_EXCEPTION)
        self._currentSingleViews[self._PEER_EXCEPTIONS_VIEW] = peerExceptions
        self._currentToolBox.addItem(peerExceptions, "Special Peers")
        
        w = QScrollArea(self)
        w.setAutoFillBackground(False)
        w.viewport().setAutoFillBackground(False)
        w.setWidgetResizable(True)
        w.setWidget(self._currentToolBox)
        w.setFrameShape(QFrame.NoFrame)
        self._settingsWidget.layout().addWidget(w)
        
    def _updateCategoryView(self):
        if self._currentToolBox is None:
            self.logger.debug("Current tool box is None. Have to reset.")
            self._createCategoryView()
            return
        
        newCategories = self._action.getPrivacyCategories()
        last = self._currentToolBox.count() - 1
        oldCategories = [convert_string(self._currentToolBox.widget(i).getCategory()) for i in xrange(last)]
        
        # remove categories that are not there any more
        reverse_enumerate = lambda l: izip(xrange(len(l)-1, -1, -1), reversed(l))
        for i, oldCat in reverse_enumerate(oldCategories):
            if oldCat not in newCategories:
                self._currentToolBox.removeItem(i)
                
        # add new categories
        lastFound = -1
        for i, newCat in reverse_enumerate(newCategories):
            if newCat in oldCategories:
                lastFound = i
            else:
                self._createAndInsertSingleView(newCat, lastFound)
        
    def _createSingleView(self, mode):
        self._clearCurrentView()
        w = SingleCategoryView(self._action, self, self.logger, mode=mode)
        self._currentSingleViews[None] = w
        self._settingsWidget.layout().addWidget(w)
        
    @loggingSlot(int)
    def _modeChanged(self, newMode, notify=True):
        if newMode == self._mode and newMode == PrivacySettings.POLICY_BY_CATEGORY:
            self._updateCategoryView()
            return
        
        self._currentToolBox = None
        if newMode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
            # single mode
            if len(self._currentSingleViews) == 0 or self._mode not in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
                # only reset if not already in single mode
                self._createSingleView(newMode)
            else:
                # only change mode
                self._currentSingleViews[None].setMode(newMode)
        elif newMode == PrivacySettings.POLICY_BY_CATEGORY:
            self._createCategoryView()
        else:
            self._clearCurrentView()
        
        self._mode = newMode
        if self._modeCombo.currentIndex() != newMode:
            self._modeCombo.setCurrentIndex(newMode)
        if notify:
            PrivacySettings.get().setPolicy(self._action, None, self._mode, applyImmediately=False, categoryPolicy=PrivacySettings.CATEGORY_NEVER)
    
    @loggingSlot(object, object)
    def _privacySettingsChanged(self, pluginName, actionName):
        if pluginName != self._action.getPluginName() or actionName != self._action.getName():
            return
        newMode = PrivacySettings.get().getPolicy(self._action, None, categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        self._modeChanged(newMode, notify=False)
        