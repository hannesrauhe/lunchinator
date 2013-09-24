from lunchinator.iface_plugins import *
from maintainer_gui import *
from lunchinator import log_debug, log_info, log_critical, get_settings
from lunchinator.lunch_datathread import DataReceiverThread

import time,subprocess    

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.reports = []
        self.w = maintainer_gui(self)
        
    def activate(self):
        iface_gui_plugin.activate(self)     
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self):
        iface_gui_plugin.create_widget(self)
        return self.w.create_widget()
    
    def destroy_widget(self):
        self.w.destroy_widget()
        iface_gui_plugin.destroy_widget(self)
            
    def add_menu(self,menu):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if "HELO_INFO" in cmd or "HELO_DICT" in cmd:
            self.w.updateInfoTable()
            self.w.update_dropdown_members()
        if cmd=="HELO_BUGREPORT_DESCR":
            self.reports.append((time.time(),ip,value))
            name = " [" + ip + "]"
            if member_info.has_key("name"):
                name = " [" + member_info["name"] + "]"
            subprocess.call(["notify-send", name, "new bug report"])            
               
        elif cmd.startswith("HELO_LOGFILE"):
            #someone will send me his logfile on tcp
            file_size=int(value.strip())
            if not os.path.exists(get_settings().main_config_dir+"/logs"):
                os.makedirs(get_settings().main_config_dir+"/logs")
            file_name=get_settings().main_config_dir+"/logs/"+str(ip)+".log"
            log_info("Receiving file of size %d on port %d"%(file_size,get_settings().tcp_port))
            dr = DataReceiverThread(ip,file_size,file_name,get_settings().tcp_port, self.w.cb_log_transfer_success, self.w.cb_log_transfer_error)
            dr.start()
            