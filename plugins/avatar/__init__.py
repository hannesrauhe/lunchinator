from lunchinator.plugin import iface_general_plugin
from avatar.l_avatar import l_avatar
import mimetypes
from lunchinator import get_server, get_settings, convert_string
from lunchinator.log import loggingFunc
from functools import partial
import os

class avatar(iface_general_plugin):
    def __init__(self):
        super(avatar, self).__init__()
        self.label = None
        self.selectedFile = None
        
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
    
    def add_menu(self,menu):
        pass    
    
    def _setImage(self, selectedFile, label):
        from PyQt4.QtGui import QImage, QPixmap
        from PyQt4.QtCore import Qt
        qimg = QImage(selectedFile)
        pixmap = QPixmap.fromImage(qimg).scaled(l_avatar.width,l_avatar.height,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        label.setToolTip(selectedFile)
    
    def parentWindow(self, w):
        return w if w.parentWidget() == None else self.parentWindow(w.parentWidget())
    
    @loggingFunc
    def _chooseFile(self):  
        from PyQt4.QtGui import QSortFilterProxyModel, QFileDialog
        class FileFilterProxyModel(QSortFilterProxyModel):
            MIME_TYPES = ["image/png", "image/jpeg", "image/gif"]
            EXTENSIONS = [u"png", u"jpg", u"jpeg", u"jpe", u"gif", u"tif", u"tiff", u"xpm"]
                
            def filterAcceptsFile(self, path):
                if os.path.isdir(path):
                    return True
                mimeType = mimetypes.guess_type(path)
                return mimeType in self.MIME_TYPES or path.split(".")[-1].lower() in self.EXTENSIONS
                
            def filterAcceptsRow(self, sourceRow, sourceParent):
                fileModel = self.sourceModel()
                index0 = fileModel.index(sourceRow, 0, sourceParent)
                path = convert_string(fileModel.filePath(index0))
                return self.filterAcceptsFile(path)
            
        fileFilter = FileFilterProxyModel()
#TODO: does not work due to a PyQt bug in some versions
#        dialog = QFileDialog(self.parentWindow(self.label), "Choose Avatar Picture:")
#        dialog.setProxyModel(fileFilter)
#        dialog.setWindowTitle("Choose Avatar Picture")
#        dialog.setFileMode(QFileDialog.ExistingFile)
#        dialog.setAcceptMode(QFileDialog.AcceptOpen)
#        if dialog.exec_():
#            selectedFiles = dialog.selectedFiles()
#            selectedFile = convert_string(selectedFiles.first())
        
        selectedFile = QFileDialog.getOpenFileName(self.parentWindow(self.label), caption="Choose Avatar Picture:")
        if selectedFile != None:
            selectedFile = convert_string(selectedFile)
            if not os.path.isdir(selectedFile) and fileFilter.filterAcceptsFile(selectedFile):
                self.selectedFile = selectedFile
                self._setImage(selectedFile, self.label)
            else:
                self.logger.error("Selected invalid file: '%s' is of invalid type", selectedFile)
        else:
            self.logger.debug("Avatar: no file selected")
    
    def _display_avatar(self):
        img_path = os.path.join(get_settings().get_avatar_dir(), get_settings().get_avatar_file())
        self._setImage(img_path, self.label)
        
    def has_options_widget(self):
        return True
        
    def create_options_widget(self, parent):
        from PyQt4.QtGui import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
        from PyQt4.QtCore import Qt
        
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.label = QLabel(widget)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.label, 0, Qt.AlignCenter)
        layout.addLayout(hlayout)
                
        b = QPushButton("Choose Picture", widget)
        b.clicked.connect(self._chooseFile)
        hlayout = QHBoxLayout()
        hlayout.addWidget(b,0, Qt.AlignCenter)
        layout.addLayout(hlayout)
        layout.addWidget(QWidget(widget), 1)
        
        self._display_avatar()
        return widget

    def save_options_widget_data(self, **_kwargs):
        if self.selectedFile != None:
            l = l_avatar(self.logger)
            l.use_as_avatar(self.selectedFile)

    def discard_changes(self):
        self._display_avatar()
