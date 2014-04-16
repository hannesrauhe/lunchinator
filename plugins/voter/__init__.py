from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import get_server, log_exception, log_error
from PyQt4.QtGui import QTreeView, QWidget, QSortFilterProxyModel, QSizePolicy, QTableWidgetItem, QPushButton
from PyQt4.QtCore import Qt, QTime
from ui_voter import Ui_Voter
import json

class voter(iface_gui_plugin):
    def __init__(self):
        super(voter, self).__init__()
        self.w = None
    
    def create_widget(self, parent):        
        self.w = voterWidget(parent)            
        return self.w
    
    def process_event(self, cmd, value, ip, member_info):
        if cmd == "HELO_VOTE":
            if not self.w:
                log_error("Voter: Vote cannot be processed")
                return
            vote = json.loads(value)
            if vote.has_key("time") and vote.has_key("place"):
                self.w.add_vote(ip, vote["place"], vote["time"])
            else:
                log_error("Voter: Vote does not look valid: " + value)

class voterWidget(QWidget):
    def __init__(self, parent):
        super(voterWidget, self).__init__(parent)
        self.ui = Ui_Voter()
        self.ui.setupUi(self)
        
        self.vote_count = {}
        self.ip2vote = {}

        self.tmp = 0
        
    def send_vote(self, place, time):
#         self.add_vote(self.tmp, place, time)
#         self.tmp += 1
        vote_call = "HELO_VOTE "+json.dumps({"place": unicode(place), "time": unicode(time)})
        get_server().call(vote_call)
        
    def vote_clicked(self):
        self.send_vote(self.ui.comboBox.currentText(), self.ui.timeEdit.text())
        
    def tablevote_clicked(self, row, column):
        print "click"
        vote_place = self.ui.tableWidget.item(row, 0).text()
        vote_time = self.ui.tableWidget.item(row, 0).text()
        self.ui.comboBox.setCurrentIndex(self.ui.comboBox.findText(vote_place))
        self.ui.timeEdit.setTime(QTime.fromString(vote_time, "HH:mm"))
        
        self.send_vote(vote_place, vote_time)
        
    def add_vote(self, ip, vote_place, vote_time):
        if self.ip2vote.has_key(ip):
            # member has already voted
            old_vote = self.ip2vote[ip]
            self.vote_count[ old_vote ] -= 1
            self.update_table_row(old_vote[0],
                                   old_vote[1],
                                   self.vote_count[ old_vote])
            
        self.ip2vote[ip] = (vote_place, vote_time)
        if self.vote_count.has_key(self.ip2vote[ip]):
            self.vote_count[ self.ip2vote[ip] ] += 1
            self.update_table_row(vote_place,
                                   vote_time,
                                   self.vote_count[ self.ip2vote[ip] ])
        else:
            self.add_place_to_dropdown(vote_place)
            self.vote_count[ self.ip2vote[ip] ] = 1     
            self.add_table_row(vote_place, vote_time)  
        
    def add_table_row(self, vote_place, vote_time, vote_count=1):
        rowIndex = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.setRowCount(rowIndex + 1)
        self.ui.tableWidget.setItem(rowIndex, 0, QTableWidgetItem(vote_place))
        self.ui.tableWidget.setItem(rowIndex, 1, QTableWidgetItem(vote_time))
        self.ui.tableWidget.setItem(rowIndex, 2, QTableWidgetItem(str(vote_count)))
        self.ui.tableWidget.setItem(rowIndex, 3, QTableWidgetItem("Vote!"))
        self.ui.tableWidget.resizeColumnsToContents()
        return rowIndex
        
    def update_table_row(self, vote_place, vote_time, vote_count):
        for rowIndex in range(0, self.ui.tableWidget.rowCount()):
            if self.ui.tableWidget.item(rowIndex, 0).text() == vote_place and self.ui.tableWidget.item(rowIndex, 1).text() == vote_time:
                self.ui.tableWidget.setItem(rowIndex, 2, QTableWidgetItem(str(vote_count)))
        
    def add_place_to_dropdown(self, place):
        self.ui.comboBox.addItem(place)
        self.ui.comboBox.model().sort(0)
        

if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window : voterWidget(window))
