from voter.ui_voter import Ui_Voter
from PyQt4.QtGui import QWidget, QTableWidgetItem
from PyQt4.QtCore import Qt, QTime
from lunchinator.log.logging_slot import loggingSlot
from lunchinator import convert_string

class voterWidget(QWidget):
    def __init__(self, parent, vote_clicked_callable, logger):
        super(voterWidget, self).__init__(parent)
        self.logger = logger
        self.ui = Ui_Voter()
        self.ui.setupUi(self)
        self.send_vote = vote_clicked_callable

    def clear_votes(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        
    @loggingSlot()
    def vote_clicked(self):
        currentText = convert_string(self.ui.comboBox.currentText())
        if currentText:
            self.send_vote(currentText, self.ui.timeEdit.time())
        
    @loggingSlot(int, int)
    def tablevote_clicked(self, row, column):
        vote_place = self.ui.tableWidget.item(row, 0).text()
        vote_time = self.ui.tableWidget.item(row, 1).text()
        self.ui.comboBox.setCurrentIndex(self.ui.comboBox.findText(vote_place))
        self.ui.timeEdit.setTime(QTime.fromString(vote_time, "HH:mm"))
        
        self.send_vote(vote_place, vote_time)
        
    def add_table_row(self, vote_place, vote_time, vote_count=1):
        insertIndex = self.ui.tableWidget.rowCount()
        # for rowIndex in range(0, self.ui.tableWidget.rowCount()):
            
                    
        self.ui.tableWidget.insertRow(insertIndex)
#         self.ui.tableWidget.setRowCount(rowIndex + 1)
        self.ui.tableWidget.setItem(insertIndex, 0, QTableWidgetItem(vote_place))
        self.ui.tableWidget.setItem(insertIndex, 1, QTableWidgetItem(vote_time))
        self.ui.tableWidget.setItem(insertIndex, 2, QTableWidgetItem(str(vote_count)))
        self.ui.tableWidget.setItem(insertIndex, 3, QTableWidgetItem("Vote!"))
        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.sortItems(1)
        self.ui.tableWidget.sortItems(0)
        self.ui.tableWidget.sortItems(2, Qt.DescendingOrder)
        return insertIndex
        
    def update_table_row(self, vote_place, vote_time, vote_count):
        for rowIndex in range(0, self.ui.tableWidget.rowCount()):
            if self.ui.tableWidget.item(rowIndex, 0).text() == vote_place and self.ui.tableWidget.item(rowIndex, 1).text() == vote_time:
                if vote_count > 0:
                    self.ui.tableWidget.setItem(rowIndex, 2, QTableWidgetItem(str(vote_count)))
                else:
                    self.ui.tableWidget.removeRow(rowIndex)
                break
        self.ui.tableWidget.sortItems(1)
        self.ui.tableWidget.sortItems(0)
        self.ui.tableWidget.sortItems(2, Qt.DescendingOrder)
        
    def add_place_to_dropdown(self, place):
        self.ui.comboBox.addItem(place)
        self.ui.comboBox.model().sort(0)