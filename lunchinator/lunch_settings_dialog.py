from PyQt4.QtGui import QTabWidget, QDialog, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt4.QtCore import Qt, pyqtSignal
from lunchinator import get_settings, get_plugin_manager, log_exception
from lunchinator.ComboTabWidget import ComboTabWidget
from bisect import bisect_left

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
        try:
            w = po.create_options_widget(self.nb)
        except:
            w = QLabel("Error while including plugin", self.nb)
            log_exception("while including plugin %s in settings window" % pName)
            
        if w:
            if pName == "General Settings":
                iPos = 0
            else:
                lo = 0
                if len(self.widget_names) > 0 and self.widget_names[0] == "General Settings":
                    lo = 1
                iPos = bisect_left(self.widget_names, pName, lo=lo)
            self.widget_names.insert(iPos, pName)
            self.nb.insertTab(iPos, w, pName)
            
    def removePlugin(self, pName):
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
            self.setMaximumSize(2000, size.height())
        
    def savePressed(self):
        self.setResult(QDialog.Accepted)
        self.closed.emit()
        self.setVisible(False)
        
    def cancelPressed(self):
        self.setResult(QDialog.Rejected)
        self.closed.emit()
        self.setVisible(False)
