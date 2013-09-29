from PyQt4.QtGui import QTabWidget, QDialog, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QComboBox, QGroupBox
from PyQt4.QtCore import Qt
from lunchinator import get_server, log_exception
from lunchinator.ComboTabWidget import ComboTabWidget

class LunchinatorSettingsDialog(QDialog):
    RESULT_SAVE = 0
    RESULT_CANCEL = -1
    
    def __init__(self, parent):
        super(LunchinatorSettingsDialog, self).__init__(parent, Qt.Dialog)
        
        self.setWindowTitle("Lunchinator Settings")
        #self.setModal(True)
        self.setResult(self.RESULT_CANCEL)
        
        contentLayout = QVBoxLayout(self)
        
        nb = ComboTabWidget(self)
        nb.setTabPosition(QTabWidget.North)
            
        plugin_widgets=[]        
        try:
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    try:
                        w = pluginInfo.plugin_object.create_options_widget(parent)
                        if w:
                            plugin_widgets.append((pluginInfo.name,w))
                    except:
                        plugin_widgets.append((pluginInfo.name,QLabel("Error while including plugin", self)))
                        log_exception("while including plugin %s in settings window" % pluginInfo.name)
        except:
            log_exception("while including plugins in settings window")
        plugin_widgets.sort(key=lambda aTuple: "" if aTuple[0] == "General Settings" else aTuple[0])
        for name,widget in plugin_widgets:
            nb.addTab(widget, name)
        
        contentLayout.addWidget(nb)
        #d.get_content_area().pack_start(nb, True, True, 0)
        if nb.count() > 0:
            nb.setCurrentIndex(0)
            
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(QWidget(self), 1)
        saveButton = QPushButton("Save", self)
        saveButton.clicked.connect(self.savePressed)
        bottomLayout.addWidget(saveButton)
        
        cancelButton= QPushButton("Cancel", self)
        cancelButton.clicked.connect(self.cancelPressed)
        bottomLayout.addWidget(cancelButton)
        
        contentLayout.addLayout(bottomLayout)
        
    def setVisible(self, visible):
        QDialog.setVisible(self, visible)
        if visible:
            size = self.size()
            self.setMinimumSize(size.width(), size.height())
            self.setMaximumSize(2000, size.height())
        
    def savePressed(self):
        self.setResult(self.RESULT_SAVE)
        self.setVisible(False)
        
    def cancelPressed(self):
        self.setVisible(False)