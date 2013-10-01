from lunchinator.iface_plugins import iface_general_plugin
from avatar.l_avatar import l_avatar
import mimetypes
from lunchinator import get_server, get_settings, log_error
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout, QComboBox, QSpinBox, QLineEdit, QCheckBox, QFileDialog, QSortFilterProxyModel, QImage, QPixmap
from PyQt4.QtCore import Qt
from functools import partial
import os

class FileFilterProxyModel(QSortFilterProxyModel):
    MIME_TYPES = ["image/png", "image/jpeg", "image/gif"]
    EXTENSIONS = ["png", "jpg", "jpeg", "jpe", "gif", "tif", "tiff", "xpm"]
        
    def filterAcceptsFile(self, path):
        if os.path.isdir(path):
            return True
        mimeType = mimetypes.guess_type(path)
        return mimeType in self.MIME_TYPES or path.split(".")[-1] in self.EXTENSIONS
        
    def filterAcceptsRow(self, sourceRow, sourceParent):
        fileModel = self.sourceModel()
        index0 = fileModel.index(sourceRow, 0, sourceParent)
        path = str(fileModel.filePath(index0).toUtf8())
        return self.filterAcceptsFile(path)

class avatar(iface_general_plugin):
    def __init__(self):
        super(avatar, self).__init__()
        self.label = None
        
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
    
    def add_menu(self,menu):
        pass    
    
    def _setImage(self, selectedFile, label):
            qimg = QImage(selectedFile)
            label.setPixmap(QPixmap.fromImage(qimg))
            label.setToolTip(selectedFile)
    
    def parentWindow(self, w):
        return w if w.parentWidget() == None else self.parentWindow(w.parentWidget())
    
    def _chooseFile(self):  
        dialog = QFileDialog(self.parentWindow(self.label), "Choose Avatar Picture:")
        fileFilter = FileFilterProxyModel()
        dialog.setProxyModel(fileFilter)
        dialog.setWindowTitle("Choose Avatar Picture")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        if dialog.exec_():
            selectedFiles = dialog.selectedFiles()
            selectedFile = str(selectedFiles.first().toUtf8())
            if not os.path.isdir(selectedFile) and fileFilter.filterAcceptsFile(selectedFile):
                l = l_avatar()
                selectedFile = l.use_as_avatar( get_settings(), selectedFile)
                self._setImage(selectedFile, self.label)
            else:
                log_error("Selected invalid file: '%s' is of invalid type" % selectedFile)
    
    def create_options_widget(self, parent):
        img_path = get_settings().get_avatar_dir()+get_settings().get_avatar_file()
        
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.label = QLabel(widget)
        layout.addWidget(self.label)
        
        self._setImage(img_path, self.label)
                
        b = QPushButton("Choose Picture", widget)
        b.clicked.connect(self._chooseFile)
        
        layout.addWidget(b)
        return widget
