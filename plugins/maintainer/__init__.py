from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_debug, log_info, log_critical, log_error, get_settings, get_server,\
    log_exception
import os, time
import subprocess    

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.options = [(("db_connect", "Which db connection to use (leave empty for default)"),"")]
        self.recorded_reports = []
        self.dbPluginErrorPrinted = False
        self.w = None
        
    def getBugsFromDB(self,mode="open"):
        stats = get_server().getDBConnection(self.options["db_connect"])
        if stats == None:
            log_error("Maintainer Plugin: Cannot read old bug reports, no DB Connection.")
            return []
        else:
            try:
                return stats.getBugsFromDB(mode)
            except:
                log_exception("Could not get bug reports from database")
                return []
        
    def activate(self):
        iface_gui_plugin.activate(self)  
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from maintainer.maintainer_gui import maintainer_gui
        iface_gui_plugin.create_widget(self, parent)
        self.w = maintainer_gui(parent, self)
        return self.w.create_widget(parent)
    
    def destroy_widget(self):
        if self.w != None:
            self.w.destroy_widget()
        iface_gui_plugin.destroy_widget(self)
            
    def add_menu(self,menu):
        pass
    
    def process_event(self,cmd,value,ip,member_info):
        if "HELO_INFO" in cmd or "HELO_DICT" in cmd:
            if self.w == None:
                return
            self.w.updateInfoTable()
            self.w.update_dropdown_members()
        if cmd=="HELO_BUGREPORT_DESCR":
            self.recorded_reports.append((time.time(),ip,value))
            name = " [" + ip + "]"
            if member_info.has_key("name"):
                name = " [" + member_info["name"] + "]"
            subprocess.call(["notify-send", name, "new bug report"])            
               
        elif cmd.startswith("HELO_LOGFILE"):
            if self.w == None:
                return
            from lunchinator.lunch_datathread_qt import DataReceiverThread
            #someone will send me his logfile on tcp
            file_size=int(value.strip())
            if not os.path.exists(get_settings().main_config_dir+"/logs"):
                os.makedirs(get_settings().main_config_dir+"/logs")
            file_name=get_settings().main_config_dir+"/logs/"+str(ip)+".log"
            log_info("Receiving file of size %d on port %d"%(file_size,get_settings().tcp_port))
            dr = DataReceiverThread(self.w, ip,file_size,file_name,get_settings().tcp_port)
            dr.successfullyTransferred.connect(self.w.cb_log_transfer_success)
            dr.errorOnTransfer.connect(self.w.cb_log_transfer_error)
            dr.start()
            
