from PyQt4.QtGui import QTabWidget, QDialog, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,\
    QDialogButtonBox
from PyQt4.QtCore import Qt, pyqtSignal
from lunchinator import get_settings, get_plugin_manager,\
    get_notification_center, convert_string
from lunchinator.log import getLogger
from lunchinator.ComboTabWidget import ComboTabWidget
from bisect import bisect_left
from lunchinator.log.logging_slot import loggingSlot

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
            getLogger().exception("while including plugin %s in settings window", self._pluginName)
            
        self.layout().addWidget(w, 1)
        
    def showEvent(self, event):
        self.showContents()
        return QWidget.showEvent(self, event)
    
    def isLoaded(self):
        return self._showing

class LunchinatorSettingsDialog(QDialog):
    save = pyqtSignal()
    discard = pyqtSignal()
    
    def __init__(self, parent):
        super(LunchinatorSettingsDialog, self).__init__(parent, Qt.Dialog)
        
        self.setWindowTitle("Lunchinator Settings")
        # self.setModal(True)
        self.setResult(QDialog.Rejected)
        
        contentLayout = QVBoxLayout(self)
        
        self.nb = ComboTabWidget(self)
        self.nb.setTabPosition(QTabWidget.North)
            
        self.widget_containers = {}
        self.widget_names = []
        try:
            if get_settings().get_plugins_enabled():
                for pluginInfo in get_plugin_manager().getAllPlugins():
                    if pluginInfo.plugin_object.is_activated:
                        self.addPlugin(pluginInfo.plugin_object,
                                       pluginInfo.name,
                                       pluginInfo.category)
        except:
            getLogger().exception("while including plugins in settings window")
        
        contentLayout.addWidget(self.nb)
        # d.get_content_area().pack_start(nb, True, True, 0)
        if self.nb.count() > 0:
            self.nb.setCurrentIndex(0)
            # show first widget
            self.nb.widget(0).showContents()
            
        buttonBox = QDialogButtonBox(Qt.Horizontal, self)
        
        saveButton = QPushButton("Save", self)
        #saveButton.setAutoDefault(True)
        saveButton.clicked.connect(self.savePressed)
        buttonBox.addButton(saveButton, QDialogButtonBox.AcceptRole)
        
        cancelButton = QPushButton("Cancel", self)
        cancelButton.clicked.connect(self.cancelPressed)
        buttonBox.addButton(cancelButton, QDialogButtonBox.RejectRole)
        
        applyButton = QPushButton("Apply", self)
        applyButton.clicked.connect(self.applyPressed)
        buttonBox.addButton(applyButton, QDialogButtonBox.ApplyRole)
        
        discardButton = QPushButton("Discard", self)
        discardButton.clicked.connect(self.discardPressed)
        buttonBox.addButton(discardButton, QDialogButtonBox.ApplyRole)
        
        contentLayout.addWidget(buttonBox)
        
        get_notification_center().connectPluginActivated(self._pluginActivated)
        get_notification_center().connectPluginWillBeDeactivated(self._pluginWillBeDeactivated)

    def finish(self):
        get_notification_center().disconnectPluginActivated(self._pluginActivated)
        get_notification_center().disconnectPluginWillBeDeactivated(self._pluginWillBeDeactivated)
        
    @loggingSlot(object, object)
    def _pluginActivated(self, pName, pCat):
        pName = convert_string(pName)
        pCat = convert_string(pCat)
        pluginInfo = get_plugin_manager().getPluginByName(pName, pCat)
        if pluginInfo is not None:
            self.addPlugin(pluginInfo.plugin_object, pName, pCat)
           
    @loggingSlot(object, object) 
    def _pluginWillBeDeactivated(self, pName, pCat):
        pName = convert_string(pName)
        pCat = convert_string(pCat)
        pluginInfo = get_plugin_manager().getPluginByName(pName, pCat)
        if pluginInfo is not None:
            self.removePlugin(pluginInfo.plugin_object, pName, pCat)
            
    def addPlugin(self, po, pName, _pCat):
        if not po.has_options_widget():
            return
        
        if po.get_displayed_name():
            displayedName = po.get_displayed_name()
        else:
            displayedName = pName
            
        w = _SettingsWidgetContainer(pName, po, self.nb)
        self.widget_containers[pName] = w
        if pName == "General Settings":
            iPos = 0
        else:
            lo = 0
            if len(self.widget_names) > 0 and self.widget_names[0] == "General Settings":
                lo = 1
            iPos = bisect_left(self.widget_names, displayedName, lo=lo)
        self.widget_names.insert(iPos, displayedName)
        self.nb.insertTab(iPos, w, displayedName)
            
    def removePlugin(self, po, pName, pCat):
        if not po.has_options_widget():
            return
         
        if self.isOptionsWidgetLoaded(pName):
            try:
                po.destroy_options_widget()
            except:
                getLogger().exception("Error destroying options widget for plugin %s from category %s", pName, pCat)
                    
        if po.get_displayed_name():
            displayedName = po.get_displayed_name()
        else:
            displayedName = pName
            
        self.widget_containers.pop(pName, None)
        # search for position
        i = bisect_left(self.widget_names, displayedName, lo=1)
        if i != len(self.widget_names) and self.widget_names[i] == displayedName:
            del self.widget_names[i]
            self.nb.removeTab(i)
        
    def setVisible(self, visible):
        QDialog.setVisible(self, visible)
        if visible:
            size = self.size()
            self.setMinimumSize(size.width(), size.height())
        
    @loggingSlot()
    def applyPressed(self):
        self.save.emit()
        
    @loggingSlot()
    def discardPressed(self):
        self.discard.emit()
        
    @loggingSlot()
    def savePressed(self):
        self.setResult(QDialog.Accepted)
        self.save.emit()
        self.setVisible(False)
        
    @loggingSlot()
    def cancelPressed(self):
        self.setResult(QDialog.Rejected)
        self.discard.emit()
        self.setVisible(False)

    def isOptionsWidgetLoaded(self, pluginName):
        if pluginName in self.widget_containers:
            return self.widget_containers[pluginName].isLoaded()
        return False
