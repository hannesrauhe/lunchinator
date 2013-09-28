import time
from lunchinator import get_server, get_settings
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QTreeWidget, QStandardItemModel, QStandardItem, QSpinBox, QTabWidget
from PyQt4 import QtCore

class maintainer_gui(object):
    def __init__(self,mt):
        self.entry = None
        self.but = None
        self.info_table = None
        self.mt = mt
        self.shown_logfile = get_settings().log_file
        self.dropdown_members = None
        self.dropdown_members_dict = None
        self.dropdown_members_model = None
        self.visible = False      
           
        
    def cb_log_transfer_success(self):
        if not self.visible:
            return False
        
        fcontent = ""
        try:
            fhandler = open(self.shown_logfile,"r")
            fcontent = fhandler.read()
            fhandler.close()
        except Exception as e:
            fcontent = "File not ready: %s"%str(e)
        self.log_area.get_buffer().set_text(fcontent)
    
    def cb_log_transfer_error(self):
        if not self.visible:
            return False
        self.log_area.get_buffer().set_text("Error while getting log")
        
    def update_reports(self):
        mode="open"
        self.bug_reports = self.mt.getBugsFromDB(mode)
        
    def display_report(self):
        if self.dropdown_reports.currentIndex()>=0:
            self.entry.get_buffer().set_text(str(self.bug_reports[self.dropdown_reports.currentIndex()][2]))
            
    def close_report(self):
        rep_nr = self.dropdown_reports.currentIndex()
        if rep_nr>=0:
            get_server().call("HELO_BUGREPORT_CLOSE %s %s"%(self.bug_reports[rep_nr][0],self.bug_reports[rep_nr][1]))        
            del self.bug_reports[rep_nr]
            self.dropdown_reports.removeItem(rep_nr)
            self.dropdown_reports.setCurrentIndex(0)
            self.display_report()

    def get_selected_log_member(self):
        member = self.dropdown_members.get_active_text()
        if member == None:
            return None
        
        if "(" in member:
            # member contains name, extract IP
            member = member[member.rfind("(")+1:member.rfind(")")]
            
        return member
    
    def request_log(self):
        member = self.get_selected_log_member()
        if member != None:
            self.log_area.get_buffer().set_text("Requesting log from "+member)
            get_server().call("HELO_REQUEST_LOGFILE %d %s"%(get_settings().tcp_port,int(self.numberchooser.get_value())),member)
            #no number_str here:
            self.shown_logfile = "%s/logs/%s.log%s"%(get_settings().main_config_dir,member,"")
        else:
            self.log_area.get_buffer().set_text("No Member selected!")
            
    def request_update(self):
        member = self.get_selected_log_member()
        if member != None:
            get_server().call("HELO_UPDATE from GUI",member)
            
    def create_reports_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.update_reports()
        self.dropdown_reports = QComboBox(widget)
        for r in self.bug_reports:
            self.dropdown_reports.addItem("%s - %s"%(time.strftime("%a, %d %b %Y %H:%M:%S",time.localtime(r[0])),r[1]))
        self.dropdown_reports.setCurrentIndex(0)
        self.display_report()
        self.close_report_btn = QPushButton("Close Bug", widget)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_reports)
        topLayout.addWidget(self.close_report_btn)
        topLayout.addWidget(QWidget(widget), 1)
        layout.addLayout(topLayout)

        layout.addWidget(QLabel("Description:", widget))
        
        self.entry = QTextEdit(widget)
        self.entry.setLineWrapMode(QTextEdit.WidgetWidth)
        self.entry.setReadOnly(True)
        layout.addWidget(self.entry)
                
        self.dropdown_reports.currentIndexChanged.connect(self.display_report)
        self.close_report_btn.clicked.connect(self.close_report)
        
        return widget
    
    def create_info_table_widget(self, parent):
        self.info_table = InfoTable(parent)
        return self.info_table
    
    def get_dropdown_member_text(self, m_ip, m_name):
        if m_ip == m_name:
            return m_ip
        else:
            return "%s (%s)" % (m_name, m_ip)
    
    def update_dropdown_members(self):
        if self.dropdown_members_model == None:
            return
        for m_ip,m_name in get_server().get_members().items():
            if not m_ip in self.dropdown_members_dict:
                # is new ip, append to the end
                self.dropdown_members_dict[m_ip] = (self.dropdown_members_model.rowCount(), m_name)
                self.dropdown_members_model.appendRow(QStandardItem(self.get_dropdown_member_text(m_ip, m_name)))
            else:
                #is already present, check if new information is available
                info = self.dropdown_members_dict[m_ip]
                if m_name != info[1]:
                    #name has changed
                    self.dropdown_members_model.setItem(info[0], 0, QStandardItem(self.get_dropdown_member_text(m_ip, m_name)))
                    self.dropdown_members_dict[m_ip] = (info[0], m_name)
                    
    def create_logs_widget(self, parent):
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        self.dropdown_members_dict = {}
        self.dropdown_members_model = QStandardItemModel()
        self.dropdown_members = QComboBox(widget)
        self.dropdown_members.setModel(self.dropdown_members_model)
        self.update_dropdown_members()
        
        self.numberchooser = QSpinBox(widget)
        self.numberchooser.setValue(0)
        self.numberchooser.setMinimum(0)
        self.numberchooser.setMaximum(10)
        self.numberchooser.setSingleStep(1)
        
        self.update_button = QPushButton("Send Update Command", widget)
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.dropdown_members)
        topLayout.addWidget(self.numberchooser)
        topLayout.addWidget(self.update_button)
        topLayout.addWidget(QWidget(widget), 1)
        layout.addLayout(topLayout)
        
        self.log_area = QTextEdit(widget)
        self.log_area.setLineWrapMode(QTextEdit.WidgetWidth)
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        self.dropdown_members.currentIndexChanged.connect(self.request_log)
        self.numberchooser.valueChanged.connect(self.request_log)
        self.update_button.clicked.connect(self.request_update)
        
        return widget
    
    def create_widget(self, parent):
        nb = QTabWidget(parent)
        nb.setTabPosition(QTabWidget.West)
        
        reports_widget = self.create_reports_widget(nb)
        logs_widget = self.create_logs_widget(nb)
        info_table_widget = self.create_info_table_widget(nb)
        
        nb.addTab(reports_widget, "Bug Reports")        
        nb.addTab(logs_widget, "Logs")        
        nb.addTab(info_table_widget, "Info")
        
        nb.setCurrentIndex(0)
        self.visible = True
        
        return nb
    
    def destroy_widget(self):
        self.visible = False
    
    def updateInfoTable(self):
        if self.info_table != None:
            self.info_table.update_model()
  
class InfoTable(QTreeWidget):
    def __init__(self, parent):
        super(InfoTable, self).__init__(parent)
        
        self.listModel = None
        self.update_model()
    
    def update_model(self):
        return None
    
        if len(get_server().member_info) == 0:
            return
        
        table_data = {"ip":[""]*len(get_server().member_info)}
        index = 0
        for ip,infodict in get_server().member_info.iteritems():
            table_data["ip"][index] = ip
            for k,v in infodict.iteritems():
                if not table_data.has_key(k):
                    table_data[k]=[""]*len(get_server().member_info)
                if False:#k=="avatar" and os.path.isfile(get_settings().avatar_dir+"/"+v):
                    # TODO add avatar image
                    table_data[k][index]="avatars/%s"%v
                else:
                    table_data[k][index]=v
            index+=1
        
        if self.listModel == None or self.listModel.columnCount() != len(table_data):
            # columns added/removed
            self.listModel = QStandardItemModel(len(get_server().member_info), len(table_data))
            headerLabels = QtCore.QStringList()
            for desc in table_data.iterkeys():
                headerLabels.append(desc)
            self.listModel.setHorizontalHeaderLabels(headerLabels)
            self.setModel(self.listModel)
            
            # todo need to add/ remove view columns?
        else:
            self.listModel.clear()

        for i in range(0,len(get_server().member_info)):
            row = []
            for k in table_data.iterkeys():
                row.append(QStandardItem(table_data[k][i]))
            self.listModel.appendRow(row)    
    
    
class maintainer_wrapper:
    reports = []
    def getBugsFromDB(self, _):
        return []
    
if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(maintainer_gui(maintainer_wrapper()))
    