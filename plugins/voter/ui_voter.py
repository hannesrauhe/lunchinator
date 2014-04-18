# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'voter.ui'
#
# Created: Thu Apr 17 13:08:03 2014
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

class Ui_Voter(object):
    def setupUi(self, Voter):
        Voter.setObjectName(_fromUtf8("Voter"))
        Voter.resize(445, 268)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Voter.sizePolicy().hasHeightForWidth())
        Voter.setSizePolicy(sizePolicy)
        self.gridLayout = QtGui.QGridLayout(Voter)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.tableWidget = QtGui.QTableWidget(Voter)
        self.tableWidget.setObjectName(_fromUtf8("tableWidget"))
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)
        self.tableWidget.setHorizontalHeaderItem(3, item)
        self.gridLayout.addWidget(self.tableWidget, 1, 0, 1, 6)
        self.label = QtGui.QLabel(Voter)
        self.label.setMaximumSize(QtCore.QSize(91, 16777215))
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtGui.QLabel(Voter)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 0, 3, 1, 1)
        self.timeEdit = QtGui.QTimeEdit(Voter)
        self.timeEdit.setObjectName(_fromUtf8("timeEdit"))
        self.gridLayout.addWidget(self.timeEdit, 0, 4, 1, 1)
        self.pushButton = QtGui.QPushButton(Voter)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.gridLayout.addWidget(self.pushButton, 0, 5, 1, 1)
        self.comboBox = QtGui.QComboBox(Voter)
        self.comboBox.setMinimumSize(QtCore.QSize(180, 0))
        self.comboBox.setEditable(True)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.gridLayout.addWidget(self.comboBox, 0, 1, 1, 1)

        self.retranslateUi(Voter)
        QtCore.QObject.connect(self.pushButton, QtCore.SIGNAL(_fromUtf8("clicked()")), Voter.vote_clicked)
        QtCore.QObject.connect(self.tableWidget, QtCore.SIGNAL(_fromUtf8("cellClicked(int,int)")), Voter.tablevote_clicked)
        QtCore.QMetaObject.connectSlotsByName(Voter)

    def retranslateUi(self, Voter):
        Voter.setWindowTitle(_translate("Voter", "Form", None))
        self.tableWidget.setSortingEnabled(False)
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("Voter", "Place", None))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("Voter", "Time", None))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("Voter", "# Votes", None))
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText(_translate("Voter", "Vote", None))
        self.label.setText(_translate("Voter", "Place:", None))
        self.label_2.setText(_translate("Voter", "Time:", None))
        self.timeEdit.setDisplayFormat(_translate("Voter", "HH:mm", None))
        self.pushButton.setText(_translate("Voter", "Vote", None))

