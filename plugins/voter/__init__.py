from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, get_settings, log_exception, log_error
from PyQt4.QtGui import QTreeView, QWidget, QSortFilterProxyModel, QSizePolicy, QTableWidgetItem, QPushButton, QPalette, QColor
from PyQt4.QtCore import Qt, QTime
from ui_voter import Ui_Voter
import json

class voter(iface_gui_plugin):
    def __init__(self):
        super(voter, self).__init__()
        self.w = None
        
        self.vote_count = {}
        self.ip2vote = {}        
    
    def create_widget(self, parent):        
        self.w = voterWidget(parent, self.send_vote)            
        return self.w
    
    def process_event(self, cmd, value, ip, member_info):
        if cmd == "HELO_VOTE":
            if not self.w:
                log_error("Voter: Vote cannot be processed")
                return
            vote = json.loads(value)
            if vote.has_key("time") and vote.has_key("place"):
                self.add_vote(ip, vote["place"], vote["time"])
            else:
                log_error("Voter: Vote does not look valid: " + value)
        
    def add_vote(self, ip, vote_place, vote_time):
        if self.ip2vote.has_key(ip):
            # member has already voted, revoke old vote
            old_vote = self.ip2vote[ip]
            self.vote_count[ old_vote ] -= 1
            if self.w:
                self.w.update_table_row(old_vote[0],
                                   old_vote[1],
                                   self.vote_count[ old_vote])
            if self.vote_count[ old_vote ] == 0:
                self.vote_count.pop(old_vote)
            
        self.ip2vote[ip] = (vote_place, vote_time)
        if self.vote_count.has_key(self.ip2vote[ip]):
            self.vote_count[ self.ip2vote[ip] ] += 1
            if self.w:
                self.w.update_table_row(vote_place,
                                   vote_time,
                                   self.vote_count[ self.ip2vote[ip] ])
        else:
            self.vote_count[ self.ip2vote[ip] ] = 1  
            if self.w: 
                self.w.add_place_to_dropdown(vote_place)  
                self.w.add_table_row(vote_place, vote_time)  
            
    
    def send_vote(self, place, stime):
        vote_call = "HELO_VOTE "+json.dumps({"place": unicode(place), "time": unicode(stime.toString("hh:mm"))})
        get_server().call(vote_call)
        get_settings().set_next_lunch_begin(stime.toString("hh:mm"))
        etime = stime.addSecs(60*30)
        get_settings().set_next_lunch_end(etime.toString("hh:mm"))
        get_server().call_info()

class voterWidget(QWidget):
    def __init__(self, parent, vote_clicked_callable):
        super(voterWidget, self).__init__(parent)
        self.ui = Ui_Voter()
        self.ui.setupUi(self)
        self.send_vote = vote_clicked_callable

    def clear_votes(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        
    def vote_clicked(self):
        if self.ui.comboBox.currentText():
            self.send_vote(self.ui.comboBox.currentText(), self.ui.timeEdit.time())
        
    def tablevote_clicked(self, row, column):
        vote_place = self.ui.tableWidget.item(row, 0).text()
        vote_time = self.ui.tableWidget.item(row, 1).text()
        self.ui.comboBox.setCurrentIndex(self.ui.comboBox.findText(vote_place))
        self.ui.timeEdit.setTime(QTime.fromString(vote_time, "HH:mm"))
        
        self.send_vote(vote_place, vote_time)
        
    def add_table_row(self, vote_place, vote_time, vote_count=1):
        insertIndex = self.ui.tableWidget.rowCount()
        #for rowIndex in range(0, self.ui.tableWidget.rowCount()):
            
                    
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
        

if __name__ == "__main__":
    def call_dummy(place,time):
        pass
    
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : voterWidget(window,call_dummy))
