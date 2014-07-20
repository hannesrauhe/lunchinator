from PyQt4.QtGui import QWidget, QComboBox, QHBoxLayout, QLabel, QToolBox,\
    QScrollArea, QFrame, QVBoxLayout
from PyQt4.QtCore import Qt
from privacy.single_category_view import SingleCategoryView
from privacy.privacy_settings import PrivacySettings

class MultipleCategoriesView(QWidget):
    def __init__(self, action, parent):
        super(MultipleCategoriesView, self).__init__(parent)

        self._action = action
        self._mode = PrivacySettings.get().getPolicy(self._action, None)
        self._currentSingleViews = []
        
        topView = self._initTopView()
        self._initSettingsWidget()
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(topView)
        mainLayout.addWidget(self._settingsWidget, 1)
        self._modeChanged(self._mode, False)
        
    def finish(self):
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
        topLayout.addWidget(QLabel(u"Accept"), 0)
        topLayout.addWidget(self._modeCombo, 1, Qt.AlignLeft)
        return topWidget
    
    def _initSettingsWidget(self):
        self._settingsWidget = QWidget(self)
        layout = QVBoxLayout(self._settingsWidget)
        layout.setContentsMargins(0, 0, 0, 0)
    
    def _clearCurrentView(self):
        for view in self._currentSingleViews:
            view.finish()
        self._currentSingleViews = []
        
        layout = self._settingsWidget.layout()
        
        child = layout.takeAt(0)
        while child != None:
            child.widget().deleteLater()
            child = layout.takeAt(0)
    
    def _createCategoryView(self):
        self._clearCurrentView()
        
        toolBox = QToolBox(self)
        
        for category in self._action.getPrivacyCategories():
            singleView = SingleCategoryView(self._action, toolBox, category)
            self._currentSingleViews.append(singleView)
            toolBox.addItem(singleView, category)
        
        w = QScrollArea(self)
        w.setWidgetResizable(True)
        w.setWidget(toolBox)
        w.setFrameShape(QFrame.NoFrame)
        self._settingsWidget.layout().addWidget(w)
        
    def _createSingleView(self, mode):
        self._clearCurrentView()
        w = SingleCategoryView(self._action, self, mode=mode)
        self._currentSingleViews.append(w)
        self._settingsWidget.layout().addWidget(w)
        
    def _modeChanged(self, newMode, notify=True):
        if newMode in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
            # single mode
            if len(self._currentSingleViews) == 0 or self._mode not in (PrivacySettings.POLICY_EVERYBODY_EX, PrivacySettings.POLICY_NOBODY_EX):
                # only reset if not already in single mode
                self._createSingleView(newMode)
            else:
                # only change mode
                self._currentSingleViews[0].setMode(newMode)
        elif newMode == PrivacySettings.POLICY_BY_CATEGORY:
            self._createCategoryView()
        else:
            self._clearCurrentView()
        
        self._mode = newMode
        if notify:
            PrivacySettings.get().setPolicy(self._action, None, self._mode)
    