from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_debug, log_info, log_critical, log_error, get_settings, get_server,\
    log_exception
import os, time
import subprocess    

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.options = [((u"db_connection", u"DB Connection", [u'auto']+get_server().getAvailableDBConnections()),"auto")]
        self.recorded_reports = []
        self.dbPluginErrorPrinted = False
        self.w = None
        
    def getBugsFromDB(self,mode="open"):
        stats = get_server().getDBConnection(self.options["db_connection"])
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
        
        get_server().controller.memberAppendedSignal.connect(self.w.info_table_model.externalRowAppended)
        get_server().controller.memberUpdatedSignal.connect(self.w.info_table_model.externalRowUpdated)
        get_server().controller.memberRemovedSignal.connect(self.w.info_table_model.externalRowRemoved)
        
        get_server().controller.memberAppendedSignal.connect(self.w.update_dropdown_members)
        get_server().controller.memberUpdatedSignal.connect(self.w.update_dropdown_members)
        get_server().controller.memberRemovedSignal.connect(self.w.update_dropdown_members)
        
        return self.w
    
    def destroy_widget(self):
        if self.w != None:
            get_server().controller.memberAppendedSignal.disconnect(self.w.info_table_model.externalRowAppended)
            get_server().controller.memberUpdatedSignal.disconnect(self.w.info_table_model.externalRowUpdated)
            get_server().controller.memberRemovedSignal.disconnect(self.w.info_table_model.externalRowRemoved)
            
            get_server().controller.memberAppendedSignal.disconnect(self.w.update_dropdown_members)
            get_server().controller.memberUpdatedSignal.disconnect(self.w.update_dropdown_members)
            get_server().controller.memberRemovedSignal.disconnect(self.w.update_dropdown_members)
            self.w.destroy_widget()
        iface_gui_plugin.destroy_widget(self)
            
    def add_menu(self,menu):
        pass
    
    def process_event(self,cmd,value,ip,_member_info):
        if cmd.startswith("HELO_LOGFILE"):
            if self.w == None:
                return
            from lunchinator.lunch_datathread_qt import DataReceiverThread
            #someone will send me his logfile on tcp
            values = value.split()
            file_size=int(values[0])
            tcp_port = 0
            if len(values) > 1:
                tcp_port = int(values[1])
            
            logDir = "%s/logs/%s" % (get_settings().get_main_config_dir(), ip)
            if not os.path.exists(logDir):
                os.makedirs(logDir)
            
            if cmd.startswith("HELO_LOGFILE_TGZ"):
                file_name="%s/tmp.tgz" % logDir
            else:
                file_name="%s/tmp.log" % logDir
            
            dr = DataReceiverThread(self.w, ip,file_size,file_name,tcp_port,category="log%s"%ip)
            dr.successfullyTransferred.connect(self.w.cb_log_transfer_success)
            dr.errorOnTransfer.connect(self.w.cb_log_transfer_error)
            dr.finished.connect(dr.deleteLater)
            dr.start()
            
