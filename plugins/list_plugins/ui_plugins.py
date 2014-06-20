# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\plugins.ui'
#
# Created: Thu Jun 12 11:47:04 2014
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Plugins(object):
    def setupUi(self, Plugins):
        Plugins.setObjectName(_fromUtf8("Plugins"))
        Plugins.resize(486, 328)
        self.gridLayout = QtGui.QGridLayout(Plugins)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.authorLabel = QtGui.QLabel(Plugins)
        self.authorLabel.setObjectName(_fromUtf8("authorLabel"))
        self.gridLayout.addWidget(self.authorLabel, 0, 1, 1, 1)
        self.descriptionlabel = QtGui.QLabel(Plugins)
        self.descriptionlabel.setWordWrap(True)
        self.descriptionlabel.setObjectName(_fromUtf8("descriptionlabel"))
        self.gridLayout.addWidget(self.descriptionlabel, 1, 1, 1, 1)
        self.label = QtGui.QLabel(Plugins)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 2, 1, 1, 1)
        self.pluginView = QtGui.QListWidget(Plugins)
        self.pluginView.setObjectName(_fromUtf8("pluginView"))
        self.gridLayout.addWidget(self.pluginView, 0, 0, 5, 1)
        self.requirementsView = QtGui.QListWidget(Plugins)
        self.requirementsView.setObjectName(_fromUtf8("requirementsView"))
        self.gridLayout.addWidget(self.requirementsView, 3, 1, 1, 1)
        self.showAllCheckBox = QtGui.QCheckBox(Plugins)
        self.showAllCheckBox.setObjectName(_fromUtf8("showAllCheckBox"))
        self.gridLayout.addWidget(self.showAllCheckBox, 5, 0, 1, 1)
        self.installReqButton = QtGui.QPushButton(Plugins)
        self.installReqButton.setObjectName(_fromUtf8("installReqButton"))
        self.gridLayout.addWidget(self.installReqButton, 4, 1, 1, 1)

        self.retranslateUi(Plugins)
        QtCore.QObject.connect(self.pluginView, QtCore.SIGNAL(_fromUtf8("currentItemChanged(QListWidgetItem*,QListWidgetItem*)")), Plugins.plugin_selected)
        QtCore.QObject.connect(self.installReqButton, QtCore.SIGNAL(_fromUtf8("clicked()")), Plugins.install_req_clicked)
        QtCore.QObject.connect(self.showAllCheckBox, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), Plugins.show_all_toggled)
        QtCore.QObject.connect(self.pluginView, QtCore.SIGNAL(_fromUtf8("itemClicked(QListWidgetItem*)")), Plugins.activate_plugin_toggled)
        QtCore.QMetaObject.connectSlotsByName(Plugins)

    def retranslateUi(self, Plugins):
        Plugins.setWindowTitle(_translate("Plugins", "Form", None))
        self.authorLabel.setText(_translate("Plugins", "Author:", None))
        self.descriptionlabel.setText(_translate("Plugins", "TextLabel", None))
        self.label.setText(_translate("Plugins", "Requirements:", None))
        self.pluginView.setSortingEnabled(True)
        self.showAllCheckBox.setText(_translate("Plugins", "Show internal plugins (always activated)", None))
        self.installReqButton.setText(_translate("Plugins", "Install Requirements", None))

