from PyQt4.QtGui import QTabWidget, QDialog, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt4.QtCore import Qt, pyqtSignal
from lunchinator import get_settings, get_plugin_manager, log_exception
from lunchinator.ComboTabWidget import ComboTabWidget
from bisect import bisect_left

class _SettingsWidgetContainer(QWidget):
    def __init__(self, pluginName, pluginObject, parent):
        super(_SettingsWidgetContainer, self).__init__(parent)
        self._pluginName = pluginName
        self._pluginObject = pluginObject
        self._showing = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
    def showContents(self):
        if self._showing:
            return
        self._showing = True
        
        try:
            w = self._pluginObject.create_options_widget(self)
        except:
            w = QLabel("Error while including plugin", self)
            log_exception("while including plugin %s in settings window" % self._pluginName)
            
        self.layout().addWidget(w, 1)
        
    def showEvent(self, event):
        self.showContents()
        return QWidget.showEvent(self, event)

class LunchinatorSettingsDialog(QDialog):
    closed = pyqtSignal()
    
    def __init__(self, parent):
        super(LunchinatorSettingsDialog, self).__init__(parent, Qt.Dialog)
        
        self.setWindowTitle("Lunchinator Settings")
        # self.setModal(True)
        self.setResult(QDialog.Rejected)
        
        contentLayout = QVBoxLayout(self)
        
        self.nb = ComboTabWidget(self)
        self.nb.setTabPosition(QTabWidget.North)
            
        self.plugin_widgets = {}
        self.widget_names = []
        try:
            if get_settings().get_plugins_enabled():
                for pluginInfo in get_plugin_manager().getAllPlugins():
                    if pluginInfo.plugin_object.is_activated:
                        if pluginInfo.plugin_object.get_displayed_name():
                            self.addPlugin(pluginInfo.plugin_object, pluginInfo.plugin_object.get_displayed_name())
                        else:
                            self.addPlugin(pluginInfo.plugin_object, pluginInfo.name)
        except:
            log_exception("while including plugins in settings window")
        
        contentLayout.addWidget(self.nb)
        # d.get_content_area().pack_start(nb, True, True, 0)
        if self.nb.count() > 0:
            self.nb.setCurrentIndex(0)
            # show first widget
            self.nb.widget(0).showContents()
            
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(QWidget(self), 1)
        saveButton = QPushButton("Save", self)
        saveButton.setAutoDefault(True)
        saveButton.clicked.connect(self.savePressed)
        bottomLayout.addWidget(saveButton)
        
        cancelButton = QPushButton("Cancel", self)
        cancelButton.clicked.connect(self.cancelPressed)
        bottomLayout.addWidget(cancelButton)
        
        contentLayout.addLayout(bottomLayout)
        
    def addPlugin(self, po, pName):
        if not po.has_options_widget():
            return
        
        w = _SettingsWidgetContainer(pName, po, self.nb)
        if pName == "General Settings":
            iPos = 0
        else:
            lo = 0
            if len(self.widget_names) > 0 and self.widget_names[0] == "General Settings":
                lo = 1
            iPos = bisect_left(self.widget_names, pName, lo=lo)
        self.widget_names.insert(iPos, pName)
        self.nb.insertTab(iPos, w, pName)
            
    def removePlugin(self, po, pName):
        try:
            po.destroy_options_widget()
        except:
            log_exception("while removing plugin %s from settings window" % pName)
            
        # search for position
        i = bisect_left(self.widget_names, pName, lo=1)
        if i != len(self.widget_names) and self.widget_names[i] == pName:
            del self.widget_names[i]
            self.nb.removeTab(i)
        
    def setVisible(self, visible):
        QDialog.setVisible(self, visible)
        if visible:
            size = self.size()
            self.setMinimumSize(size.width(), size.height())
        
    def savePressed(self):
        self.setResult(QDialog.Accepted)
        self.closed.emit()
        self.setVisible(False)
        
    def cancelPressed(self):
        self.setResult(QDialog.Rejected)
        self.closed.emit()
        self.setVisible(False)
