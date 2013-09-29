from lunchinator.iface_plugins import *
from maintainer_gui import *
from lunchinator import log_debug, log_info, log_critical
from lunchinator.lunch_datathread import DataReceiverThread
import os

import subprocess    

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.options = [(("use_different_db", "Use specific HANA instance"),False),
                        (("hana_server", "HANA Server"),""),
                        (("hana_port", "Port for HANA DB") ,30015),
                        (("hana_user", "HANA User Name"),""),
                        (("hana_pass", "Password for HANA User"),"")]
        self.stats = None
        self.recorded_reports = []
        self.dbPluginErrorPrinted = False
        self.w = maintainer_gui(self)
        
    def getDB(self):
        if self.options["use_different_db"]:
            if self.stats == None:
                try:
                    from database_connection.stat_db import hdb_stat_db
                    self.stats = hdb_stat_db()
                    self.stats.connect(self.options["hana_server"],self.options["hana_port"],self.options["hana_user"],self.options["hana_pass"])
                except ImportError:
                    if not self.dbPluginErrorPrinted:
                        log_warning("database plugin not available")
                        self.dbPluginErrorPrinted = True
            return self.stats
        else:
            dbplugin = PluginManagerSingleton.get().getPluginByName("Database Connection", "general")
            if dbplugin == None:
                return None
            return dbplugin.plugin_object.stats
        
    def getBugsFromDB(self,mode="open"):
        stats = self.getDB()
        if stats == None:
            log_error("Maintainer Plugin: Cannot read old bug reports, no DB Connection.")
            return []
        else:
            return stats.getBugsFromDB(mode)
        
    def activate(self):
        iface_gui_plugin.activate(self)  
        
    def deactivate(self):
        if self.stats != None:
            self.stats.close()
            self.stats= None
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        iface_gui_plugin.create_widget(self, parent)
        return self.w.create_widget(parent)
    
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
            self.recorded_reports.append((time.time(),ip,value))
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
            