from PyQt4.QtGui import QItemDelegate, QStyleOptionComboBox, QStyle,\
    QApplication, QComboBox
from PyQt4.QtCore import Qt, QSize, pyqtSignal
from lunchinator.log.logging_slot import loggingSlot
from lunchinator import convert_string

class ComboboxDelegate(QItemDelegate):
    def __init__(self, column, parent):
        super(ComboboxDelegate, self).__init__(parent)
        self._column = column
        self._editor = None

    def paint(self, painter, option, index):
        if index.column() is self._column:
            comboBoxOption = QStyleOptionComboBox()
            comboBoxOption.rect = option.rect
            comboBoxOption.currentText = index.data(Qt.DisplayRole).toString()
            if convert_string(comboBoxOption.currentText) == u"Default":  
                comboBoxOption.state = QStyle.State_Active
            else:  
                comboBoxOption.state = QStyle.State_Active | QStyle.State_Enabled
            comboBoxOption.frame = True
            QApplication.style().drawComplexControl(QStyle.CC_ComboBox, comboBoxOption, painter)
            QApplication.style().drawControl(QStyle.CE_ComboBoxLabel, comboBoxOption, painter)
        else:
            super(ComboboxDelegate, self).paint(painter, option, index)
     
    def sizeHint(self, option, index):
        if index.column() is self._column:
            return QSize(option.rect.size().width(), 25)
            
        return QItemDelegate.sizeHint(self, option, index)
     
    def getEditor(self):
        return self._editor
    
    @loggingSlot()
    def editorClosing(self):
        self._editor = None
    
    class OpeningComboBox(QComboBox):
        hiding = pyqtSignal()
        
        def showEvent(self, event):
            QComboBox.showEvent(self, event)
            self.showPopup()
     
        def hideEvent(self, event):
            self.hiding.emit()
            return QComboBox.hideEvent(self, event)
     
    def createEditor(self, parent, _option, index):
        editor = self.OpeningComboBox(parent)
        if index.column() is self._column:
            editor.addItems([u"Default",
                             u"Debug",
                             u"Info",
                             u"Warning",
                             u"Error",
                             u"Critical"])
            editor.setCurrentIndex(editor.findText(index.data(Qt.DisplayRole).toString(), Qt.MatchExactly))
            editor.currentIndexChanged.connect(self._commitEditor)

        self._editor = editor
        self._editor.hiding.connect(self.editorClosing)            
        return editor
     
    @loggingSlot(int)
    def _commitEditor(self, _newIndex):
        self.commitData.emit(self._editor)
        #self.closeEditor.emit(self._editor, QItemDelegate.SubmitModelCache)
        #self._editor = None

    def setEditorData(self, comboBox, index):
        if index.column() is self._column:
            value = index.model().data(index, Qt.DisplayRole).toString()
            #set the index of the combo box
            comboBox.setCurrentIndex(comboBox.findText(value, Qt.MatchExactly))
     
    def setModelData(self, comboBox, model, index):
        if index.column() is self._column:
            model.setData(index, comboBox.currentText(), Qt.EditRole)
